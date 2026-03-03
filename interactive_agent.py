import asyncio
import httpx
import os
import sys
import json
import glob
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Ensure stdin and stdout use utf-8 on Windows for proper Korean/Emoji handling
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')

URL_READ = "http://127.0.0.1:8000/api/v1/hwpx/read"
URL_MODIFY = "http://127.0.0.1:8000/api/v1/hwpx/modify"
URL_OLLAMA = "http://localhost:11435/api/chat"
MODEL_NAME = "gemma3:12b" # Update this to your standard model

DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

def clean_text(text):
    if not isinstance(text, str): return text
    return text.encode('utf-16', 'surrogatepass').decode('utf-16', 'ignore').replace('\udceb', '').replace('\udced', '')
    
def sanitize_obj(obj):
    if isinstance(obj, str):
        return clean_text(obj)
    elif isinstance(obj, list):
        return [sanitize_obj(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: sanitize_obj(v) for k, v in obj.items()}
    return obj

def save_debug_log(module_name: str, filename: str, content: str):
    """Saves string content to a specific folder under debug/."""
    if not DEBUG_MODE: return
    debug_dir = os.path.join("debug", module_name)
    os.makedirs(debug_dir, exist_ok=True)
    filepath = os.path.join(debug_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

async def send_to_ollama(messages: list) -> str:
    """Sends the conversation history to Ollama and returns the response."""
    
    # Strictly strip all surrogates/invalid chars before sending to httpx
    def strict_clean(text):
        if not isinstance(text, str): return text
        return text.encode('utf-8', 'ignore').decode('utf-8')
        
    cleaned_messages = []
    for m in messages:
        cleaned_messages.append({
            "role": m["role"],
            "content": strict_clean(m["content"])
        })
        
    payload = {
        "model": MODEL_NAME,
        "messages": cleaned_messages,
        "stream": False
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(URL_OLLAMA, json=payload, timeout=120.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "")
            else:
                return f"Error from Ollama: {response.text}"
        except Exception as e:
            return f"Connection error: {e}"

async def read_hwpx_blocks(file_path: str) -> list:
    """Uses the /read API to extract text blocks from a HWPX file."""
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
            try:
                res = await client.post(URL_READ, files=files, timeout=10.0)
                if res.status_code == 200:
                    return res.json().get('blocks', [])
                return []
            except httpx.ConnectError:
                print("\n🚨 [연결 오류] 백엔드 API 서버(FastAPI)와 연결할 수 없습니다.")
                print("   문서를 파싱하려면 먼저 터미널을 열고 다음 명령어를 실행해 서버를 켜주세요:")
                print("   👉 uv run uvicorn src.app.main:app --host 127.0.0.1 --port 8000\n")
                sys.exit(1)

async def modify_hwpx(file_path: str, modifications: list) -> str:
    """Uses the /modify API to apply JSON modifications to the HWPX file."""
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
            data = {"modifications": json.dumps(modifications)}
            res = await client.post(URL_MODIFY, files=files, data=data, timeout=30.0)
            
            if res.status_code == 200:
                result_dir = "result"
                if not os.path.exists(result_dir):
                    os.makedirs(result_dir)
                
                # Append YYYYMMDD_HHMM to the filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                base_name, ext = os.path.splitext(os.path.basename(file_path))
                output_filename = f"{base_name}_{timestamp}{ext}"
                output_filepath = os.path.join(result_dir, output_filename)
                
                with open(output_filepath, "wb") as out_f:
                    out_f.write(res.content)
                return output_filepath
            else:
                raise Exception(f"Modify API Failed: {res.text}")

async def main():
    print("==================================================")
    print(" 🤖 대화형 HWPX 공문 작성 에이전트 시작 ")
    print("==================================================\n")
    
    # 1. Load Available Templates
    template_dir = "templates"
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
        
    templates = glob.glob(os.path.join(template_dir, "*.hwpx"))
    if not templates:
        print(f"[{template_dir}] 폴더에 HWPX 양식 문서가 없습니다. 양식을 먼저 넣어주세요.")
        return
        
    print(f"✅ 총 {len(templates)}개의 양식 문서가 로드되었습니다.")
    
    summary_path = os.path.join(template_dir, "summary.json")
    
    if os.path.exists(summary_path):
        print(f"🔍 캐시된 양식 요약 정보({os.path.basename(summary_path)})를 불러옵니다...")
        with open(summary_path, "r", encoding="utf-8") as f:
            template_summaries = json.load(f)
    else:
        print("🔍 각 양식의 내용을 최초 분석하여 요약 캐시(summary.json)를 생성하는 중입니다. (최초 1회, 일시적으로 시간이 소요됨)")
        template_summaries = {}
        for i, t in enumerate(templates):
            filename = os.path.basename(t)
            print(f" - [{i+1}/{len(templates)}] '{filename}' 분석 중...")
            raw_blocks = await read_hwpx_blocks(t)
            blocks = sanitize_obj(raw_blocks)
            
            blocks_dump = json.dumps(blocks[:50], ensure_ascii=False)
            summarize_prompt = f"""다음은 '{filename}' 파일에서 파싱된 텍스트 블록의 앞부분입니다:
{blocks_dump}

이 문서의:
1) 주된 사용 목적
2) 작성 시 필수 입력 항목(이름, 날짜, 소속 등 본문 빈칸 추론)

위 두 가지를 각각 1~2줄로 짧게 요약해주세요. 마크다운 없이 평문으로 대답하세요."""
            
            summary = await send_to_ollama([{"role": "user", "content": summarize_prompt}])
            template_summaries[filename] = summary.strip()
            
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(template_summaries, f, ensure_ascii=False, indent=2)
        print("✅ 캐시 생성 완료!")
        
    # 2. Initial User Input & Template Selection
    print("\n--------------------------------------------------")
    print("🤖 비서: 안녕하세요! 어떤 공문을 작성해 드릴까요?")
    print("         (예: 내일 체육대회 건으로 휴가 쓰고 싶어. 내 이름은 홍길동이야.)")
    print("--------------------------------------------------\n")
    
    first_input = input("👤 사용자: ")
    if first_input.lower() in ['exit', 'quit', '종료']:
        print("강제 종료합니다.")
        return
        
    print("🤖 비서가 사용자의 요청과 양식 내용을 비교하여 적절한 문서를 고르는 중입니다...")
    
    summary_lines = []
    for filename, summary in template_summaries.items():
        summary_lines.append(f"[파일명: {filename}]\n요약 설명:\n{summary}")
    template_list_str = "\n\n".join(summary_lines)
    
    classifier_prompt = f"""당신은 사용자의 요청을 분석하여 가장 알맞은 문서 양식을 골라주는 분류기입니다.
다음은 현재 사용 가능한 양식 목록과 각 양식의 요약된 정보입니다:

{template_list_str}

사용자의 처음 요청: "{first_input}"

위 요약 정보를 바탕으로 사용자의 요청을 처리하기 위해 가장 적합한 양식의 '파일명'만 정확하게 대답하세요. 부연 설명 없이 정확히 파일명만 출력해야 합니다.
"""
    
    selected_filename = await send_to_ollama([{"role": "user", "content": classifier_prompt}])
    selected_filename = selected_filename.strip().replace('"', '').replace("'", "")
    
    # Validation
    selected_template = None
    for t in templates:
        if os.path.basename(t) in selected_filename:
            selected_template = t
            break
            
    if not selected_template:
         print(f"⚠️ LLM이 정확한 양식을 찾지 못했습니다. (응답: {selected_filename}) 기본 양식을 사용합니다.")
         selected_template = templates[0]
         
    print(f"\n📄 선택된 양식: {os.path.basename(selected_template)}")
    
    # 2. Read Document Structure
    print("\n🔍 문서 구조를 분석하는 중입니다...")
    raw_blocks = await read_hwpx_blocks(selected_template)
    if not raw_blocks:
        print("❌ 문서 구조를 읽는 데 실패했습니다.")
        return
        
    blocks = sanitize_obj(raw_blocks)
        
    if DEBUG_MODE:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_blocks_json = json.dumps(blocks, ensure_ascii=False, indent=2)
        save_debug_log("document_analysis", f"full_document_structure_{timestamp}.json", full_blocks_json)
        print("\n[DEBUG] 🚀 전체 문서 구조 데이터(Full JSON)가 debug/document_analysis/ 폴더에 저장되었습니다.")
        
    # 3. Setup System Prompt
    blocks_json = json.dumps(blocks[:120], ensure_ascii=False, indent=2) # Send up to 120 blocks context
    
    if DEBUG_MODE:
        save_debug_log("document_analysis", f"llm_context_blocks_{timestamp}.json", blocks_json)
        
    system_prompt = f"""당신은 사용자의 요청을 받아 한글 문서(HWPX)의 특정 부분(Block)을 수정하는 군용 비서입니다.
현재 선택된 템플릿: {os.path.basename(selected_template)}

[문서 구조 (block_id 및 텍스트 모음)]
{blocks_json}

[역할 및 규칙]
1. 사용자가 문서 양식에 필요한 모든 정보를 제공했는지 확인하십시오. (예: 날짜, 작성자 이름, 부대명 등 군 공문에 필수적인 내용)
2. 정보가 부족하다면, 사용자에게 친절하게 질문하여 정보를 수집하십시오. 
3. 모든 정보가 수집되었다면, 문서의 어떤 `block_id`의 `target_text`를 어떤 `replace_text`로 바꿀지 JSON 배열 형식으로만 응답해야 합니다.
4. JSON을 출력할 준비가 될 때까지는 일반적인 한국어 대화로 응답하세요.

[동적 표 행 추가 (Dynamic Table Expansion) 규칙]
- 만약 사용자가 "목록" 형태의 데이터를 제공했고 (예: 물품 3개), 템플릿의 표(table)에 빈 행이 1개밖에 없다면, 당신은 임의로 block_id의 행 번호(`rN`)를 증가시켜서 JSON에 포함할 수 있습니다.
- 예: 템플릿에 `sec0_tbl0_r1_c0` (내용: '품명') 하나만 있어도, 
     물품 1: "block_id": "sec0_tbl0_r1_c0", "target_text": "품명", "replace_text": "물"
     물품 2: "block_id": "sec0_tbl0_r2_c0", "target_text": "품명", "replace_text": "라면"
     물품 3: "block_id": "sec0_tbl0_r3_c0", "target_text": "품명", "replace_text": "햇반"
     위와 같이 존재하지 않는 로우 인덱스(`r2`, `r3`)를 만들어서 제공해도 됩니다. 엔진이 자동으로 표에 행을 추가해 넣습니다.
- 중요❗: 새롭게 추가하는 행의 `target_text`는 반드시 기존에 템플릿에 존재하던 '기준 행'(예: r1)의 `target_text`와 **정확히 동일**해야 합니다. (엔진이 기준 행을 그대로 복사하기 때문입니다.)

결과 생성 시 JSON 형식:
```json
[
  {{
    "block_id": "sec0_p1",
    "target_text": "원본 텍스트",
    "replace_text": "사용자가 입력한 새로운 텍스트"
  }}
]
```
JSON 코드 블록 안에만 최종 결과를 출력하세요.
"""
    
    history = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": first_input}
    ]
    
    # 4. Interactive Loop
    is_first_turn = True
    while True:
        if not is_first_turn:
            user_input = input("👤 사용자: ")
            if user_input.lower() in ['exit', 'quit', '종료']:
                print("강제 종료합니다.")
                break
            history.append({"role": "user", "content": user_input})
        else:
            # First turn logic: we already have first_input in history from above
            is_first_turn = False
            
        print("🤖 비서가 생각 중입니다...")
        llm_response = await send_to_ollama(history)
        
        # Check if the LLM thinks it's done and returned JSON
        # A simple heuristic: if it contains "block_id" and [ it's probably the JSON payload
        if '"block_id"' in llm_response and '[' in llm_response:
            
            if DEBUG_MODE:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_debug_log("llm_responses", f"llm_raw_payload_{timestamp}.json", llm_response)
                
                history_copy = history + [{"role": "assistant", "content": llm_response}]
                save_debug_log("conversation", f"history_{timestamp}.json", json.dumps(history_copy, ensure_ascii=False, indent=2))
                
                print("\n[DEBUG] 🚀 LLM 단일 원본 응답 및 대화 내역이 debug/ 폴더에 저장되었습니다.")
                
            print("\n🤖 비서: 네, 필요한 정보가 모두 준비되었습니다! 문서를 자동 작성합니다...")
            
            # Clean up potential markdown backticks from LLM output just in case
            cleaned_json_str = llm_response.replace('```json', '').replace('```', '').strip()
            
            # Handle case where LLM might return just the JSON block mixed with other text
            start_idx = cleaned_json_str.find('[')
            end_idx = cleaned_json_str.rfind(']')
            if start_idx != -1 and end_idx != -1:
                 cleaned_json_str = cleaned_json_str[start_idx:end_idx+1]
                 
            try:
                raw_modifications = json.loads(cleaned_json_str)
                # Map 'text' to 'replace_text' if LLM got confused by the read schema
                modifications = []
                for mod in raw_modifications:
                    if "replace_text" not in mod and "text" in mod:
                        mod["replace_text"] = mod["text"]
                    if "target_text" not in mod:
                         mod["target_text"] = "" # Fallback
                    modifications.append(mod)
                    
                if DEBUG_MODE:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_debug_log("api_requests", f"modify_payload_{timestamp}.json", json.dumps(modifications, ensure_ascii=False, indent=2))
                    print("\n[DEBUG] 🚀 백엔드 /modify API로 전송되는 파싱된 데이터가 debug/api_requests/ 폴더에 저장되었습니다.")
                    
                # Call Modify API
                output_path = await modify_hwpx(selected_template, modifications)
                print(f"\n🎉 짝짝짝! 문서 작성이 완료되었습니다! 파일명: {output_path}")
            except json.JSONDecodeError:
                print(f"\n❌ LLM이 유효하지 않은 JSON을 반환했습니다.\n내용: {cleaned_json_str}")
            except Exception as e:
                print(f"\n❌ 문서 수정 중 오류 발생: {e}")
                
            break # Exit the loop after generating the document
        else:
            # It's a regular conversation response
            print(f"\n🤖 비서: {llm_response}\n")
            history.append({"role": "assistant", "content": llm_response})
            
            if DEBUG_MODE:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_debug_log("llm_responses", f"llm_chat_{timestamp}.txt", llm_response)
                save_debug_log("conversation", f"history_{timestamp}.json", json.dumps(history, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
