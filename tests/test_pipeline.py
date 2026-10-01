import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from evidence_desk.core import ROOT, run_query, verify_trace, retrieve, load_corpus
from evidence_desk.evaluation import evaluate, save_report


class PipelineTests(unittest.TestCase):
    def test_synthetic_entities_have_expected_states(self):
        for entity, status in [('Atlas Reserve','VERIFIED'),('Bramble Custody','REVIEW'),('Cinder Protocol','ABSTAIN'),('Delta Vault','ABSTAIN'),('Echo Ledger','VERIFIED'),('Fjord Reserve','VERIFIED'),('Gale Custody','ABSTAIN'),('Harbor Token','ABSTAIN'),('Juniper Fund','ABSTAIN')]:
            with self.subTest(entity=entity):
                result=run_query(entity,'What is the reserve coverage ratio?')
                self.assertEqual(result['status'],status)
                self.assertTrue(verify_trace(result['trace']))
                if status != 'VERIFIED': self.assertEqual(result['claims'],[])

    def test_direct_metric_and_ratio_values(self):
        for question, value, unit in [('reserves','124000000','USD'),('liabilities','100000000','USD'),('coverage ratio','1.2400','x')]:
            with self.subTest(question=question):
                claim=run_query('Atlas Reserve',question)['claims'][0]
                self.assertEqual((claim['value'],claim['unit']),(value,unit))

    def test_unknown_entity_abstains(self):
        self.assertEqual(run_query('No Such Issuer','reserve ratio')['status'],'ABSTAIN')

    def test_request_validation(self):
        for entity, question in [('', 'reserves'),('x',''),('x','a'*1001),([], 'reserves'),('x',None)]:
            with self.subTest(entity=entity,question=question):
                with self.assertRaises(ValueError): run_query(entity,question)
        with self.assertRaises(ValueError): run_query('Atlas Reserve','reserves',as_of='bad-date')

    def test_consequential_inference_abstains(self):
        for question in ['Is this solvent?', 'Is this safe?', 'Assess fraud risk', 'Is this entity creditworthy?']:
            with self.subTest(question=question):
                self.assertEqual(run_query('Atlas Reserve',question)['status'],'ABSTAIN')

    def test_retrieval_does_not_drop_conflicting_documents(self):
        docs=retrieve(load_corpus(),'Bramble Custody','Treasury reserve summary')
        self.assertEqual({d.id for d in docs},{'bramble-main','bramble-recon'})

    def test_trace_determinism(self):
        self.assertEqual(run_query('Atlas Reserve','reserves'),run_query('Atlas Reserve','reserves'))


class EvaluationAndCliTests(unittest.TestCase):
    def test_benchmark_keeps_known_failures(self):
        result=evaluate()
        self.assertEqual(len(result['cases']),19)
        self.assertEqual(result['checked']['decision_correct'],17)
        self.assertEqual(result['checked']['unsafe_accepted'],1)
        self.assertEqual(result['checked']['false_abstentions'],1)
        self.assertEqual({r['id'] for r in result['cases'] if not r['checked_correct']},{'forecast-qualification','supported-paraphrase'})

    def test_metrics_are_computed_from_labels(self):
        result=evaluate()
        unsafe=[r for r in result['cases'] if not r['safe_to_accept']]
        for prefix in ['baseline','checked']:
            self.assertEqual(result[prefix]['unsafe_accepted'],sum(r[prefix+'_status']=='VERIFIED' for r in unsafe))
            self.assertEqual(result[prefix]['total'],len(result['cases']))

    def test_report_files_are_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            result=save_report(Path(directory))
            self.assertEqual(json.loads((Path(directory)/'evaluation.json').read_text()),result)
            self.assertEqual(len((Path(directory)/'evaluation.csv').read_text().splitlines()),20)
            self.assertIn('forecast',(Path(directory)/'evaluation.md').read_text().lower())

    def test_cli_ask_and_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'trace.json'
            result=subprocess.run([sys.executable,'-m','evidence_desk','ask','--output',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'],'VERIFIED')
            checked=subprocess.run([sys.executable,'-m','evidence_desk','verify-trace',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(checked.returncode,0)
            data=json.loads(path.read_text());data['trace'][0]['detail']['entity']='tampered';path.write_text(json.dumps(data))
            checked=subprocess.run([sys.executable,'-m','evidence_desk','verify-trace',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(checked.returncode,1)

    def test_cli_invalid_input_is_nonzero(self):
        result=subprocess.run([sys.executable,'-m','evidence_desk','ask','--as-of','not-a-date'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,2)


if __name__=='__main__': unittest.main()
