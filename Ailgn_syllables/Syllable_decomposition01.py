import json
import re
import unicodedata

VOWELS = frozenset('aeiouʉéɨ')
CODAS = frozenset(('y', 'w', 'n', 'ng'))


def get_syllables(word, *, preserve_case=False):
    """以八個母音估計音節；韻尾 y/w/n/ng 後立即切開。

    ng 視為單一單位。沒有緊接母音的 n/ng 保留為可獨立的子音
    音節結尾；y/w 位於音節開頭時仍可接母音。其他音節沿用
    母音間保留最後一個子音給下一音節的規則。韻尾後剩餘的
    無母音片段獨立保留，不重新接回已結束的音節。
    """
    if not word:
        return []
    word = unicodedata.normalize('NFC', word)
    if not preserve_case:
        word = word.lower()
    syllables = []
    for part in re.split(r'[\s-]+', word):
        if not part:
            continue
        # 先綁定 ng，避免切割點落在 n 與 g 之間。
        tokens = re.findall(r'ng|.', part, flags=re.IGNORECASE)
        lowered = [token.lower() for token in tokens]
        nuclei = []
        for i, token in enumerate(lowered):
            if token in VOWELS:
                nuclei.append(i)
            elif token in ('n', 'ng') and (i == 0 or lowered[i - 1] not in VOWELS):
                nuclei.append(i)
        if not nuclei:
            syllables.append(part)
            continue
        start = 0
        for pos, nucleus in enumerate(nuclei):
            if lowered[nucleus] in ('n', 'ng'):
                end = nucleus + 1
            elif nucleus + 1 < len(tokens) and lowered[nucleus + 1] in CODAS:
                end = nucleus + 2
            elif pos + 1 < len(nuclei):
                following = nuclei[pos + 1]
                end = following if following == nucleus + 1 else following - 1
            else:
                end = len(tokens)
            if end > start:
                syllables.append(''.join(tokens[start:end]))
            start = end
        if start < len(tokens):
            syllables.append(''.join(tokens[start:]))
    return syllables


def process_data_payload(data):
    """
    直接處理 Python Dictionary 資料，回傳處理後的 List
    """
    output_data = []
    
    # 針對原始資料格式遍歷
    for ch_word, content in data.items():
        if "new_word" in content:
            for item in content["new_word"]:
                fm_word = item.get("fm_word", "")
                ch_semantic = item.get("ch_semantic", "")
                fm_words = fm_word if isinstance(fm_word, list) else [fm_word]

                for current_fm_word in fm_words:
                    if not isinstance(current_fm_word, str) or not current_fm_word:
                        continue

                    # 取得音節列表 (全小寫)
                    sylls = get_syllables(current_fm_word)
                    
                    # 建立單字資料物件
                    word_entry = {
                        "chinese_word": ch_word,
                        "amis_word": current_fm_word,  # 保留原始大小寫
                        "ch_semantic": ch_semantic,
                        "syllables": sylls,         # 音節陣列
                        "syllable_count": len(sylls)
                    }
                    output_data.append(word_entry)
    return output_data

def model_main(input_file):
    """保留舊接口以防單獨呼叫"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"錯誤: 找不到檔案 {input_file}")
        return "[]"

    result_list = process_data_payload(data)
    return json.dumps(result_list, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    # 測試用
    pass
