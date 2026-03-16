import json
import os

# ==========================================
# 設定與路徑
# ==========================================

# 1. 統計檔案所在的資料夾 (原本 get_syllable_count 用)
STATS_FOLDER = "音節統計結果"

# 2. 原始字典檔對照表 (新功能用，對應到原始 JSON 檔名)
# 這是從您的 syllabify_word.py 複製過來的，用來定位原始檔案
RAW_DICT_FILES = {
    "01_阿美語": "01_ilrdf_dict_Amis.json",
    "02_泰雅語": "02_ilrdf_dict_Atayal.json",
    "03_排灣語": "03_ilrdf_dict_Paiwan.json",
    "04_布農語": "04_ilrdf_dict_Bunun.json",
    "05_卑南語": "05_ilrdf_dict_Puyuma.json",
    "06_魯凱語": "06_ilrdf_dict_Rukai.json",
    "07_鄒語": "07_ilrdf_dict_Tsou.json",
    "08_賽夏語": "08_ilrdf_dict_SaySiyat.json",
    "09_雅美語": "09_ilrdf_dict_Tao.json",
    "10_邵語": "10_ilrdf_dict_Thao.json",
    "11_噶瑪蘭語": "11_ilrdf_dict_Kavalan.json",
    "12_太魯閣語": "12_ilrdf_dict_Truku.json",
    "13_撒奇萊雅語": "13_ilrdf_dict_Sakizaya.json",
    "14_賽德克語": "14_ilrdf_dict_Seediq.json",
    "15_拉阿魯哇語": "15_ilrdf_dict_Hla'alua.json",
    "16_卡那卡那富語": "16_ilrdf_dict_Kanakanavu.json"
}

# 語言名稱對照表 (輸入名稱 -> 內部標準名稱)
LANG_MAP = {
    "Amis": "01_阿美語",       "阿美語": "01_阿美語",
    "Atayal": "02_泰雅語",     "泰雅語": "02_泰雅語",
    "Paiwan": "03_排灣語",     "排灣語": "03_排灣語",
    "Bunun": "04_布農語",      "布農語": "04_布農語",
    "Puyuma": "05_卑南語",     "卑南語": "05_卑南語",
    "Rukai": "06_魯凱語",      "魯凱語": "06_魯凱語",
    "Tsou": "07_鄒語",         "鄒語": "07_鄒語",
    "SaySiyat": "08_賽夏語",   "賽夏語": "08_賽夏語",
    "Tao": "09_雅美語",        "雅美語": "09_雅美語",
    "Thao": "10_邵語",         "邵語": "10_邵語",
    "Kavalan": "11_噶瑪蘭語",  "噶瑪蘭語": "11_噶瑪蘭語",
    "Truku": "12_太魯閣語",    "太魯閣語": "12_太魯閣語",
    "Sakizaya": "13_撒奇萊雅語", "撒奇萊雅語": "13_撒奇萊雅語",
    "Seediq": "14_賽德克語",   "賽德克語": "14_賽德克語",
    "Hla'alua": "15_拉阿魯哇語", "拉阿魯哇語": "15_拉阿魯哇語",
    "Kanakanavu": "16_卡那卡那富語", "卡那卡那富語": "16_卡那卡那富語"
}

# 用來快取已讀取的原始字典內容，避免重複 IO
_RAW_DICT_CACHE = {}

# ==========================================
# 函式定義
# ==========================================

def get_syllable_count(target_syllable, language_name):
    """
    查詢特定語言中，某個音節出現的次數 (讀取 syllabify_word.py 產生的統計檔)。
    """
    file_prefix = LANG_MAP.get(language_name)
    
    if not file_prefix:
        print(f"⚠️  錯誤：找不到語言名稱 '{language_name}'，請檢查拼字。")
        return 0

    # 這裡預設讀取「聲韻母合併統計」，因為這包含了最完整的拆解資訊
    # 如果您需要讀取其他檔案 (如純音節統計)，請修改這裡的後綴
    json_filename = f"{file_prefix}_聲韻母合併統計.json"
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, STATS_FOLDER, json_filename)
    
    if not os.path.exists(file_path):
        # 嘗試回退到上一層目錄找 (以防執行位置不同)
        parent_dir = os.path.dirname(current_dir)
        file_path = os.path.join(parent_dir, STATS_FOLDER, json_filename)
        
        if not os.path.exists(file_path):
            print(f"⚠️  找不到統計檔案：{file_path}")
            return 0
            
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get(target_syllable, 0)
    except Exception as e:
        print(f"❌ 讀取統計檔失敗: {e}")
        return 0


def get_raw_string_count(target_string, language_name):
    """
    直接在原始字典檔 (01_ilrdf_dict_Amis.json 等) 中搜尋字串出現次數。
    不經過音節切割邏輯，而是直接計算字串出現頻率。
    
    Args:
        target_string (str): 要搜尋的字串 (例如 "ma")
        language_name (str): 語言名稱 (例如 "Amis")
        
    Returns:
        int: 該字串在所有詞彙中出現的總次數
    """
    # 1. 取得標準語言名稱 (如 01_阿美語)
    lang_key = LANG_MAP.get(language_name)
    if not lang_key:
        print(f"⚠️  錯誤：找不到語言名稱 '{language_name}'")
        return 0
        
    # 2. 取得原始 JSON 檔名
    raw_filename = RAW_DICT_FILES.get(lang_key)
    if not raw_filename:
        print(f"⚠️  錯誤：找不到 '{lang_key}' 對應的原始字典檔名")
        return 0

    # 3. 檢查快取，如果沒有載入過該語言字典，則讀取檔案
    global _RAW_DICT_CACHE
    if lang_key not in _RAW_DICT_CACHE:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 假設原始字典檔跟此 script 在同一層，或是上一層
        # 根據您的 syllabify_word.py，它們似乎在同一層
        file_path = os.path.join(current_dir, raw_filename)
        
        if not os.path.exists(file_path):
            # 嘗試上一層 (如果此 script 被放在子資料夾 fm_dict 中)
            file_path = os.path.join(os.path.dirname(current_dir), raw_filename)
            
        if not os.path.exists(file_path):
            print(f"⚠️  找不到原始字典檔案：{raw_filename}")
            return 0
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                _RAW_DICT_CACHE[lang_key] = json.load(f)
        except Exception as e:
            print(f"❌ 讀取原始字典失敗: {e}")
            return 0

    # 4. 開始統計
    # 從快取中取得資料
    data = _RAW_DICT_CACHE[lang_key]
    total_count = 0
    target = target_string.lower() # 轉小寫以進行不分大小寫比對
    
    # data 的 key 是族語單字，value 是解釋
    for word in data.keys():
        # 計算 target 在 word 中出現的次數 (例如 "banana".count("na") = 2)
        # 確保比對時都轉為小寫
        total_count += word.lower().count(target)
        
    return total_count
