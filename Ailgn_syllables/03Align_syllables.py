import os
import json
file_path = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE_PATH = os.path.join(file_path, '音節轉字典.json')
OUTPUT_FILE_PATH =  os.path.join(file_path, 'aligned_syllables.json')
DICT_FILE_PATH = os.path.join(file_path, 'cedict_normalized.json')
def find_word_in_dict(word, dictionary):
    """在字典中尋找單詞，返回其拼音列表"""
    pinyin = [None] * len(word)
    cnt = 0
    for entry in dictionary:
        key = entry.get("traditional", "")
        if key in word:
            cnt += 1
            entry_pinyin = entry.get('pronunciations', [])
            initial = entry_pinyin[0].get('initial', '') if entry_pinyin else ''
            final = entry_pinyin[0].get('final', '') if entry_pinyin else ''
            pinyin[word.index(key)] = initial + "," + final
        if cnt >= len(word) + 1:  # 已找到足夠的拼音
            break
    
    return pinyin

def process_file(input_path: str, dict_path: str, output_path: str):
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
    except FileNotFoundError:
        print(f"❌ 錯誤：找不到檔案 '{input_path}'")
        print("請檢查檔名是否正確，或是檔案是否在正確的資料夾中。")
        return  # 直接結束函式，不往下執行
        
    except json.JSONDecodeError:
        print(f"❌ 錯誤：檔案 '{input_path}' 內容不是有效的 JSON 格式")
        return  # 直接結束函式
    
    try:
        with open(dict_path, "r", encoding="utf-8") as f:
            dictionary = json.load(f)
    except FileNotFoundError:
        print(f"❌ 錯誤：找不到字典檔案 '{dict_path}'")
        print("請檢查檔名是否正確，或是檔案是否在正確的資料夾中。")
        return
    except json.JSONDecodeError:
        print(f"❌ 錯誤：檔案 '{dict_path}' 內容不是有效的 JSON 格式")
        return  # 直接結束函式
    
    result = []
    for item in data:
        word = item.get("chinese_word", "")
        # print(f"處理: {word}")
        ch_semantic = item.get("ch_semantic", "")
        syllable_structure = item.get("syllable_structure", [])
        pinyin_info = []
        for syl in syllable_structure:
            pinyin_info.append(syl.get("split_display", ""))
        pinyin_ch = find_word_in_dict(word, dictionary)
        result.append({
            "chinese": word,
            "ch_semantic": ch_semantic,
            "pinyin_info": pinyin_info,
            "dict_pinyin": pinyin_ch
        })
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # base_path = "新詞整合/新詞譯詞/"
    process_file(INPUT_FILE_PATH, DICT_FILE_PATH, OUTPUT_FILE_PATH)