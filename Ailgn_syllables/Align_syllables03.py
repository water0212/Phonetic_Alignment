import os
import json
import Syllable_decomposition01
import Syllable_dictionary02

# 路徑設定
current_dir = os.path.dirname(os.path.abspath(__file__))
INPUT_FOLDER_NAME = "16族_中借詞_清洗版"
OUTPUT_FOLDER_NAME = "Aligned_Results" # 輸出資料夾名稱
DICT_FILENAME = "ch_dict.json"
CEDICT_FILENAME = "cedict_normalized.json"

def is_cjk_char(ch):
    return "\u4e00" <= ch <= "\u9fff"


def normalize_pinyin_token(token):
    if token is None:
        return ""
    return token.strip().lower().replace("ü", "ㄩ")


def strip_tone(token):
    token = normalize_pinyin_token(token)
    if token and token[-1].isdigit():
        return token[:-1]
    return token


def parse_token_to_ift(token):
    normalized = normalize_pinyin_token(token)
    if not normalized:
        return "0c", "0v", ""

    tone = ""
    base = normalized
    if normalized[-1].isdigit():
        tone = normalized[-1]
        base = normalized[:-1]

    initial, final = Syllable_dictionary02.split_syllable_by_initials(base)
    if not initial:
        initial = "0c"
    if not final:
        final = "0v"

    return initial, final, tone


def build_cedict_index(cedict_data):
    index = {}
    for entry in cedict_data:
        traditional = entry.get("traditional", "")
        pronunciations = entry.get("pronunciations", [])
        if not traditional:
            continue

        if traditional not in index:
            index[traditional] = []

        for p in pronunciations:
            index[traditional].append({
                "pinyin": normalize_pinyin_token(p.get("pinyin", "")),
                "initial": p.get("initial", "") or "0c",
                "final": p.get("final", "") or "0v",
                "tone": p.get("tone", "")
            })
    return index


def get_word_pinyin_tokens(word, ch_dict):
    entry = ch_dict.get(word)
    if not entry:
        return []

    pinyin_value = entry.get("pinyin", "")
    if not pinyin_value:
        return []

    if isinstance(pinyin_value, str):
        raw_tokens = [t for t in pinyin_value.split() if t.strip()]
        return [normalize_pinyin_token(t) for t in raw_tokens]

    if isinstance(pinyin_value, list):
        raw_tokens = []
        for item in pinyin_value:
            if isinstance(item, str):
                raw_tokens.extend([t for t in item.split() if t.strip()])
            elif isinstance(item, dict):
                py = item.get("pinyin", "")
                if isinstance(py, str):
                    raw_tokens.extend([t for t in py.split() if t.strip()])
        return [normalize_pinyin_token(t) for t in raw_tokens]

    return []


def select_pronunciation(char, target_token, cedict_index):
    pronunciations = cedict_index.get(char, [])
    if not pronunciations:
        return None

    target_norm = normalize_pinyin_token(target_token)
    target_no_tone = strip_tone(target_norm)
    target_initial, target_final, target_tone = parse_token_to_ift(target_norm)

    if target_norm:
        exact_if_candidates = [
            p for p in pronunciations
            if p.get("initial", "") == target_initial and p.get("final", "") == target_final
        ]
        if exact_if_candidates:
            if target_tone:
                for p in exact_if_candidates:
                    if p.get("tone", "") == target_tone:
                        return p
            return exact_if_candidates[0]

        for p in pronunciations:
            if p.get("pinyin", "") == target_norm:
                return p

        for p in pronunciations:
            if strip_tone(p.get("pinyin", "")) == target_no_tone:
                return p

    return pronunciations[0]


def align_word_to_initial_final(word, ch_dict, cedict_index):
    tokens = get_word_pinyin_tokens(word, ch_dict)
    has_word_level_tokens = bool(tokens)

    if not has_word_level_tokens:
        fallback_tokens = []
        for ch in word:
            if not is_cjk_char(ch):
                continue
            pronunciations = cedict_index.get(ch, [])
            if pronunciations:
                fallback_tokens.append(pronunciations[0].get("pinyin", ""))
        tokens = fallback_tokens

    char_alignment = []
    dict_pinyin = []

    same_length = len(tokens) == len(word)
    cjk_token_idx = 0

    for idx, ch in enumerate(word):
        token = ""

        if same_length:
            token = tokens[idx]
        elif is_cjk_char(ch):
            if cjk_token_idx < len(tokens):
                token = tokens[cjk_token_idx]
                cjk_token_idx += 1

        if not is_cjk_char(ch):
            continue

        selected = select_pronunciation(ch, token, cedict_index)
        if selected:
            initial = selected.get("initial", "0c")
            final = selected.get("final", "0v")
            matched_pinyin = selected.get("pinyin", "")
        else:
            initial, final = "0c", "0v"
            matched_pinyin = ""

        char_alignment.append({
            "char": ch,
            "target_pinyin": token,
            "matched_pinyin": matched_pinyin,
            "initial": initial,
            "final": final
        })
        dict_pinyin.append(f"{initial},{final}")

    return {
        "word_pinyin": " ".join(tokens),
        "word_pinyin_tokens": tokens,
        "char_alignment": char_alignment,
        "dict_pinyin": dict_pinyin
    }

def process_alignment_payload(data_list, ch_dict, cedict_index):
    result = []
    
    for item in data_list:
        word = item.get("chinese_word", "")
        ch_semantic = item.get("ch_semantic", "")
        syllable_structure = item.get("syllable_structure", [])
        
        pinyin_info = []
        for syl in syllable_structure:
            pinyin_info.append(syl.get("split_display", ""))

        aligned = align_word_to_initial_final(word, ch_dict, cedict_index)
        
        if not aligned["dict_pinyin"]:
            print(f"⚠️ 無法對齊 '{word}' 的拼音，請檢查字典資料。")

        result.append({
            "chinese": word,
            "ch_semantic": ch_semantic,
            "pinyin_info": pinyin_info,
            # "word_pinyin": aligned["word_pinyin"],
            # "word_pinyin_tokens": aligned["word_pinyin_tokens"],
            "dict_pinyin": aligned["dict_pinyin"]
        })
    return result

def main():
    # 1. 設定路徑
    input_dir = os.path.join(current_dir, INPUT_FOLDER_NAME)
    output_dir = os.path.join(current_dir, OUTPUT_FOLDER_NAME)
    dict_path = os.path.join(current_dir, DICT_FILENAME)
    cedict_path = os.path.join(current_dir, CEDICT_FILENAME)

    # 檢查輸入資料夾與字典
    if not os.path.exists(input_dir):
        print(f"❌ 找不到輸入資料夾: {input_dir}")
        return
    if not os.path.exists(dict_path):
        print(f"❌ 找不到字典檔: {dict_path}")
        return
    if not os.path.exists(cedict_path):
        print(f"❌ 找不到字典檔: {cedict_path}")
        return

    # 建立輸出資料夾
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 已建立輸出資料夾: {output_dir}")

    # 2. 預先載入字典 (只讀一次，提升效能)
    print(f"📖 正在載入字典 {DICT_FILENAME} ...")
    with open(dict_path, "r", encoding="utf-8") as f:
        ch_dict = json.load(f)
    print("✅ ch_dict 載入完成。")

    print(f"📖 正在載入字典 {CEDICT_FILENAME} ...")
    with open(cedict_path, "r", encoding="utf-8") as f:
        cedict_data = json.load(f)
    cedict_index = build_cedict_index(cedict_data)
    print("✅ cedict_normalized 載入完成。")

    # 3. 遍歷資料夾內所有檔案
    files = [f for f in os.listdir(input_dir) if f.endswith(".json")]
    print(f"🔍 發現 {len(files)} 個 JSON 檔案，準備處理...")

    for filename in files:
        input_filepath = os.path.join(input_dir, filename)
        output_filepath = os.path.join(output_dir, f"aligned_{filename}")
        
        print(f"🚀 正在處理: {filename} ...")
        
        try:
            # Step A: 讀取原始檔案
            with open(input_filepath, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)

            # Step B: 執行 Syllable_decomposition01 (音節拆解)
            step1_data = Syllable_decomposition01.process_data_payload(raw_data)

            # Step C: 執行 Syllable_dictionary02 (結構分析)
            step2_data = Syllable_dictionary02.process_structure_payload(step1_data)

            # Step D: 執行 Align_syllables03 (拼音對齊)
            final_data = process_alignment_payload(step2_data, ch_dict, cedict_index)

            # Step E: 寫入結果
            with open(output_filepath, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)
            
            print(f"   💾 已儲存至: {output_filepath}")

        except Exception as e:
            print(f"   ⚠️ 處理 {filename} 時發生錯誤: {e}")

    print("\n🎉 所有檔案處理完成！")

if __name__ == "__main__":
    main()
