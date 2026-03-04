import os

from src.app.infra.hwpx_tool import HwpxTool

tool = HwpxTool()
# Create a dummy section XML to test apply_modifications.
try:
    os.makedirs("temp_test", exist_ok=True)
    xml_content = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <hp:secDef xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
        <hp:p id="0">
            <hp:run>
                <hp:t>Original Text</hp:t>
            </hp:run>
        </hp:p>
    </hp:secDef>
    """
    with open("temp_test/section0.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)

    modifications = [
        {
            "block_id": "sec0_p0",
            "target_text": "Original Text",
            "replace_text": "Line 1\nLine 2\nLine 3",
        }
    ]
    tool.apply_modifications("temp_test/section0.xml", modifications, 0)

    with open("temp_test/section0.xml", encoding="utf-8") as f:
        print(f.read())
except Exception as e:
    print("Error:", e)
