import json
import os
import Syllable_decomposition01

# ==========================================
# 核心定義
# ==========================================
INITIALS = ['zh', 'ch', 'sh','ts', 'b', 'p', 'm', 'f', 'd', 't', 'n', 'l', #ts為邵族聲母 
            'g', 'k', 'h', 'j', 'q', 'x', 'r', 'z', 'c', 's', 'v','’','^'] 

# 依照長度排序 ensure zh, ch, sh match first
INITIALS.sort(key=len, reverse=True)

def split_syllable_by_initials(syllable):
    if not syllable:
        return "", ""

    syllable = syllable.lower()
    curr_initial = ""
    curr_final = syllable

    for ini in INITIALS:
        if syllable.startswith(ini):
            curr_initial = ini
            curr_final = syllable[len(ini):]
            break
    
    return curr_initial, curr_final

def process_structure_payload(data_list):
    """
    接收 List[Dict] (來自 decomposition 的輸出)，
    為每個 entry 增加 syllable_structure
    """
    for entry in data_list:
        syllables = entry.get("syllables", [])
        structure_list = []
        
        for syl in syllables:
            # # 1. 處理 w -> u
            # if 'w' in syl:
            #     syl = syl.replace('w', 'u')
            #     while 'uu' in syl: syl = syl.replace('uu', 'u')
            
            # # 2. 處理 y -> i
            # if 'y' in syl:
            #     syl = syl.replace('y', 'i')
            #     while 'ii' in syl: syl = syl.replace('ii', 'i')

            ini, fin = split_syllable_by_initials(syl)
            
            # 空值補 0c / 0v
            if not ini: ini = "0c"
            if not fin: fin = "0v"

            display_str = f"{ini},{fin}"
            
            structure_list.append({
                "original": syl, 
                "initial": ini,
                "final": fin,
                "split_display": display_str
            })
        
        entry["syllable_structure"] = structure_list
    
    return data_list

def model_main(input_file):
    """保留舊接口"""
    # 先執行音節拆解
    json_str_from_step1 = Syllable_decomposition01.model_main(input_file)
    data = json.loads(json_str_from_step1)
    
    # 執行結構分析
    result_data = process_structure_payload(data)
    
    return json.dumps(result_data, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    pass
