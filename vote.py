import json
import os

order = [
    "b", "p", "m", "f", "d", "t", "n", "l",
    "g", "k", "h", "j", "q", "x", "zh", "ch",
    "sh", "r", "z", "c", "s",
    "an", "en", "ang", "eng", "er",
    "i", "u", "u:",
    "a", "o", "ㄜ", "e",
    "ai", "ei", "ao", "ou",
    "ia", "io", "ie", "iai", "iao", "iou",
    "ian", "in", "iang", "ing",
    "ua", "uo", "uai", "ui", "uan", "un", "uang", "ong",
    "u:e", "u:an", "u:n", "iong"
]

file_path = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(file_path, 'output_alignment_refined.json')
output_file = os.path.join(file_path, '16_output_alignment_voted.json')

def vote_alignment(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # vote_count = {}
    vote_count = {k: {} for k in order}
    for item in data:
        alignments = item['alignment']
        if not alignments:
            continue
        # Count votes for each alignment
        for alignment in alignments:
            if alignment.get('status') == "已匹配" or alignment.get('status') == "已匹配(合併)":
                ch = alignment.get('chinese_syllable')
                tsou = alignment.get('tsou_syllable')
                initial_ch = ch.get('initial')
                final_ch = ch.get('final')
                tsou_initial = tsou.get('initial')
                tsou_final = tsou.get('final')

                if initial_ch not in vote_count.keys():
                    vote_count[initial_ch] = {}
                if tsou_initial not in vote_count[initial_ch]:
                    vote_count[initial_ch][tsou_initial] = 0
                vote_count[initial_ch][tsou_initial] += 1
                # print(vote_count)
                if final_ch not in vote_count.keys():
                    vote_count[final_ch] = {}
                if tsou_final not in vote_count[final_ch]:
                    vote_count[final_ch][tsou_final] = 0
                vote_count[final_ch][tsou_final] += 1
                
                    


    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(vote_count, f, ensure_ascii=False, indent=4)



if __name__ == "__main__":
    vote_alignment(input_file, output_file)