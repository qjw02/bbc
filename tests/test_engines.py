import copy
import json
import unittest
import tempfile
from datetime import timedelta
from pathlib import Path

from scripts.indicators import structure, timestamp
from scripts.macro_engine import evaluate_macro
from scripts.signal_engine import SIGNALS, analyze, load_config

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / 'evals/fixtures/true_breakout.json').read_text(encoding='utf-8'))


def set_metrics(data, values):
    for name, value in values.items():
        data['metrics'][name]['value'] = value


def mirror_rows(rows):
    for row in rows:
        o,h,l,c = (row[k] for k in ('open','high','low','close'))
        row.update(open=200-o, high=200-l, low=200-h, close=200-c)


def mutate(data, name):
    cfg = load_config()
    s = structure(data['candles']['1H'], cfg['technical'])
    rows = data['candles']['1H']
    if name == 'false_breakout':
        rows[-1]['close'] = s['resistance'] - .15
        rows[-1]['low'] = min(rows[-1]['low'], rows[-1]['close']-.1)
    elif name == 'chase':
        data['quote']['price'] += 5*s['atr']
    elif name == 'mirror':
        for rows in data['candles'].values(): mirror_rows(rows)
        data['quote']['price'] = 200-data['quote']['price']
    elif name == 'opposite_4h':
        mirror_rows(data['candles']['4H'])
    elif name == 'single_close':
        rows[-2].update(open=s['resistance']-.3,high=s['resistance']-.02,low=s['resistance']-.5,close=s['resistance']-.1)
    elif name == 'stale':
        data['metrics']['oi_change_pct_1h']['observed_at'] = '2026-09-01T00:00:00Z'
    elif name == 'sweep':
        for row in rows[-2:]:
            row.update(open=s['resistance']-.2,high=s['resistance']+.3,low=s['resistance']-.4,close=s['resistance']-.1)


class EngineTests(unittest.TestCase):
    def test_evaluation_scenarios(self):
        cases=json.loads((ROOT/'evals/evals.json').read_text(encoding='utf-8'))['cases']
        for case in cases:
            with self.subTest(case=case['id']):
                data=fixture()
                set_metrics(data,case.get('metrics',{}))
                mutate(data,case.get('mutation'))
                result=analyze(data)
                self.assertEqual(result['signal'],case['expected_signal'],result['reasons'])
                self.assertEqual(result['plan'] is not None,case['plan'])
                if 'expected_regime' in case:
                    self.assertEqual(result['macro']['regime'],case['expected_regime'])
                if 'reason' in case:
                    self.assertIn(case['reason'],' '.join(result['reasons']))

    def test_all_nine_regimes(self):
        samples={
            'Neutral/Range':{},
            'Liquidity Risk-On':dict(fed_assets_change_usd_bn_7d=20,tga_change_usd_bn_7d=-20,rrp_change_usd_bn_7d=-20,stablecoin_change_pct_7d=2),
            'Normal Risk-On':dict(nasdaq_change_pct_1d=1,sp500_change_pct_1d=.5),
            'Inflation Shock':dict(oil_change_pct_1d=4,ust10y_change_bp_1d=15,tips10y_change_bp_1d=7,nasdaq_change_pct_1d=-2),
            'Fed Tightening Shock':dict(fed_hawkish=1,ust2y_change_bp_1d=15,tips10y_change_bp_1d=8),
            'Carry Trade Unwind':dict(usdjpy_change_pct_1h=-1,jgb10y_change_bp_1d=12,jgb30y_change_bp_1d=18,nikkei_change_pct_1d=-2,nasdaq_change_pct_1d=-2),
            'Credit Stress':dict(hy_spread_change_bp_1d=30,vix=35,move=150),
            'War/Oil Shock':dict(war_risk=1,oil_change_pct_1d=7),
            'Crypto-native Leverage Flush':dict(oi_change_pct_1h=-8,liquidations_z_1h=4,price_change_pct_1h=-4)}
        for regime,values in samples.items():
            with self.subTest(regime=regime):
                data=fixture(); set_metrics(data,values)
                self.assertEqual(evaluate_macro(data,load_config())['regime'],regime)

    def test_plan_geometry_and_worst_entry_rr(self):
        for side in ('long','short'):
            data=fixture()
            if side=='short': mutate(data,'mirror')
            result=analyze(data); plan=result['plan']
            self.assertIsNotNone(plan,result['reasons'])
            low,high=plan['entry_zone']
            if side=='long': self.assertTrue(plan['invalidation']<low<high<plan['tp1']<plan['tp2'])
            else: self.assertTrue(plan['tp2']<plan['tp1']<low<high<plan['invalidation'])
            self.assertGreaterEqual(plan['net_rr_tp1']+1e-9,1.5)

    def test_invalid_market_inputs_wait(self):
        changes=[lambda d:d['candles']['1H'][-1].update(high=0),
                 lambda d:d['candles']['1H'][-1].update(close=float('nan')),
                 lambda d:d['candles']['15m'].pop(-3),
                 lambda d:d['quote'].update(price=True),
                 lambda d:d['quote'].update(as_of='2026-09-01T00:00:00Z'),
                 lambda d:d.update(symbol='SOL'),
                 lambda d:d['candles'].update({'4H':[]}),
                 lambda d:d.update(as_of='2026-09-18T12:00:00')]
        for change in changes:
            data=fixture(); change(data); result=analyze(data)
            self.assertEqual(result['signal'],'WAIT')
            self.assertIsNone(result['plan'])

    def test_missing_future_wrong_unit_metrics(self):
        for mode in ('missing','future','unit','nan','source','horizon','bool'):
            with self.subTest(mode=mode):
                data=fixture(); item=data['metrics']['vix']
                if mode=='missing': del data['metrics']['vix']
                elif mode=='future': item['available_at']='2026-09-19T00:00:00Z'
                elif mode=='unit': item['unit']='pct'
                elif mode=='nan': item['value']=float('nan')
                elif mode=='source': item['source']=''
                elif mode=='horizon': item['horizon']='1m'
                elif mode=='bool': item['value']=False
                result=analyze(data)
                self.assertEqual(result['signal'],'WAIT')
                self.assertIn('vix',result['macro']['missing_required'])

    def test_unclosed_and_future_candles_do_not_confirm(self):
        data=fixture(); data['candles']['1H'][-1]['closed']=False
        self.assertEqual(analyze(data)['signal'],'WAIT')
        data=fixture(); base=analyze(data)
        row=copy.deepcopy(data['candles']['1H'][-1])
        row['close_time']='2026-09-18T13:00:00Z'
        row.update(open=999,high=1001,low=998,close=1000)
        data['candles']['1H'].append(row)
        self.assertEqual(analyze(data),base)

    def test_dynamic_prices_scale_and_examples_ignored(self):
        data=fixture(); cfg=load_config(); before=analyze(data,cfg)
        cfg['illustrative_levels_only']['BTC']=[1,9999999]
        self.assertEqual(analyze(data,cfg),before)
        for rows in data['candles'].values():
            for row in rows:
                for key in ('open','high','low','close'): row[key]*=700
        data['quote']['price']*=700
        after=analyze(data,cfg)
        self.assertEqual(after['signal'],before['signal'])
        self.assertAlmostEqual(after['plan']['invalidation'],before['plan']['invalidation']*700)
        data['symbol']='ETH'
        self.assertEqual(analyze(data,cfg)['signal'],'LONG BIAS')

    def test_multiple_risks_flush_is_not_masked(self):
        data=fixture()
        set_metrics(data,dict(hy_spread_change_bp_1d=30,vix=35,move=150,oi_change_pct_1h=-9,liquidations_z_1h=4,price_change_pct_1h=-4))
        result=analyze(data)
        self.assertEqual(result['macro']['regime'],'Credit Stress')
        self.assertIn('Crypto-native Leverage Flush',result['macro']['active_regimes'])
        self.assertEqual(result['signal'],'WAIT')

    def test_flow_headwinds_and_event_and_crowding(self):
        cases=[dict(etf_flow_usd_m=-100,stablecoin_change_pct_7d=-2,cme_basis_annual_pct=-1),
               dict(event_risk=1),dict(oi_change_pct_1h=8,funding_pct_8h=.08)]
        for values in cases:
            data=fixture(); set_metrics(data,values)
            self.assertEqual(analyze(data)['signal'],'WAIT')

    def test_japan_spreads_and_transition(self):
        data=fixture(); data['previous_regime']='Carry Trade Unwind'
        result=evaluate_macro(data,load_config())
        self.assertTrue(result['changed'])
        self.assertAlmostEqual(result['japan']['spreads']['ust_jgb_10y_bp'],300)
        self.assertAlmostEqual(result['japan']['curves']['jgb_10y_30y_bp'],120)

    def test_nearby_obstacle_blocks_plan(self):
        data=fixture()
        row=data['candles']['4H'][-5]
        row['high']=data['quote']['price']+.1
        result=analyze(data)
        self.assertEqual(result['signal'],'WAIT')
        self.assertIn('reward/risk',' '.join(result['reasons']))

    def test_breakout_does_not_move_tested_level(self):
        data=fixture(); cfg=load_config()['technical']
        initial=structure(data['candles']['1H'],cfg)
        data['candles']['1H'][-2]['high']+=20
        after=structure(data['candles']['1H'],cfg)
        self.assertEqual(initial['resistance'],after['resistance'])
        self.assertEqual(initial['atr'],after['atr'])

    def test_unclosed_interior_gap_and_non_object(self):
        data=fixture(); data['candles']['1H'][-3]['closed']=False
        self.assertEqual(analyze(data)['signal'],'WAIT')
        for value in (None, [], 5, 'bad'):
            self.assertEqual(analyze(value)['signal'],'WAIT')

    def test_invalid_configuration_rejected(self):
        for mode in ('cost','coverage','stop','rule'):
            cfg=load_config()
            if mode=='cost': cfg['roundtrip_cost_bps']=-1
            elif mode=='coverage': cfg['minimum_coverage']=2
            elif mode=='stop': cfg['technical']['stop_buffer_atr']=.01
            else: cfg['regimes']['Credit Stress']['rules'][0][1]='=='
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'config.json'
                path.write_text(json.dumps(cfg),encoding='utf-8')
                with self.assertRaises(ValueError): load_config(path)


if __name__=='__main__': unittest.main()
