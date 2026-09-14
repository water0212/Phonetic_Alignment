import importlib.util
import json
from pathlib import Path
import re
import sys
import unicodedata
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Ailgn_syllables'))
import Syllable_decomposition01 as decomposition
import Syllable_dictionary02 as structure
import Align_syllables03 as alignment


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


statistics = load_module('statistics_syllables', ROOT / 'fm_dict' / 'syllabify_word.py')
phonetic = load_module('phonetic', ROOT / '04Phonetic_Alignment.py')


class SyllableRulesTest(unittest.TestCase):
    def test_boundaries(self):
        cases = {
            '': [], 'aeiouʉéɨ': list('aeiouʉéɨ'),
            'aya': ['ay', 'a'], 'awa': ['aw', 'a'],
            'ana': ['an', 'a'], 'anga': ['ang', 'a'],
            'ayt': ['ay', 't'], 'awkr': ['aw', 'kr'],
            'ant': ['an', 't'], 'angk': ['ang', 'k'],
            'angra': ['ang', 'ra'], 'axia': ['a', 'xi', 'a'],
            'ng': ['ng'], 'ngay': ['ng', 'ay'], 'nka': ['n', 'ka'],
            'ya': ['ya'], 'wa': ['wa'], 'xyw': ['xyw'],
            'karta': ['kar', 'ta'], 'ai': ['a', 'i'],
            'ay wa\tng-a': ['ay', 'wa', 'ng', 'a'],
            'KE\u0301N': ['kén'],
        }
        for word, expected in cases.items():
            with self.subTest(word=word):
                self.assertEqual(decomposition.get_syllables(word), expected)

    def test_ng_structure(self):
        entry = structure.process_structure_payload([{'syllables': ['ng', 'ang']}])[0]
        self.assertEqual(entry['syllable_structure'][0]['split_display'], '0c,ng')
        self.assertEqual(entry['syllable_structure'][1]['split_display'], '0c,ang')

    def test_custom_dictionary(self):
        self.assertEqual(alignment.CEDICT_FILENAME, 'cedict_parsed_custom.json')
        data = json.loads((ROOT / 'Ailgn_syllables' / alignment.CEDICT_FILENAME).read_text(encoding='utf-8'))
        index = alignment.build_cedict_index(data)
        for entry in data:
            for pronunciation in entry['pronunciations']:
                expected = dict(pronunciation)
                expected['pinyin'] = alignment.normalize_pinyin_token(expected['pinyin'])
                expected['initial'] = expected.get('initial') or '0c'
                expected['final'] = expected.get('final') or '0v'
                self.assertIn(expected, index[entry['traditional']])

    def test_glide_orphans_prefer_left_even_when_right_scores_higher(self):
        aligner = phonetic.PhoneticAligner()
        aligner.calculate_similarity = lambda ch, ts: len(ts['final']) if ch['pinyin'] == 'right' else 0
        parse = phonetic.parse_pinyin_string
        for glide in ('y', 'w'):
            for token in (f'0c,{glide}a', f'{glide},a'):
                with self.subTest(token=token):
                    original = [({'pinyin': 'left'}, parse('k,a'), '已匹配'),
                                (None, parse(token), '中文缺失'),
                                ({'pinyin': 'right'}, parse('t,a'), '已匹配')]
                    refined, history = aligner.refine_alignment(original)
                    self.assertEqual(refined[0][1]['final'], 'a' + glide + 'a')
                    self.assertEqual(history[0]['decision'], '向左合併(y/w開頭)')
                    self.assertGreater(history[0]['delta_right'], history[0]['delta_left'])
                    self.assertEqual(len(original), 3)
        refined, _ = aligner.refine_alignment([(None, parse('0c,wa'), '中文缺失')])
        self.assertEqual(len(refined), 1)

    def test_consonant_merge_does_not_leak_placeholders(self):
        aligner = phonetic.PhoneticAligner()
        result = aligner.merge_syllables(phonetic.parse_pinyin_string('k,0v'),
                                        phonetic.parse_pinyin_string('t,a'))
        self.assertEqual(result['final'], 'ta')

    def test_all_dictionary_words_preserve_spelling_and_share_rules(self):
        count = 0
        for path in (ROOT / 'fm_dict').glob('*_ilrdf_dict_*.json'):
            data = json.loads(path.read_text(encoding='utf-8'))
            for word in data:
                syllables = decomposition.get_syllables(word)
                expected = re.sub(r'[\s-]+', '', unicodedata.normalize('NFC', word).lower())
                self.assertEqual(''.join(syllables), expected, word)
                actual = statistics.syllabify_word(word)
                self.assertEqual(actual.lower().split('-'), syllables, word)
                self.assertNotIn('', syllables, word)
                # Every original ng survives as an intact digraph.
                self.assertEqual(sum(s.count('ng') for s in syllables), word.lower().count('ng'), word)
                count += 1
        self.assertGreater(count, 1000)
        print(f'Checked {count} dictionary words')


if __name__ == '__main__':
    unittest.main()
