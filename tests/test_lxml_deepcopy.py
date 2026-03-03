import copy
from lxml import etree

_HP_NS = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
etree.register_namespace("hp", "http://www.hancom.co.kr/hwpml/2011/paragraph")

xml_str = """
<hp:tbl xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
    <hp:tr>
        <hp:tc><hp:p><hp:run><hp:t>Header 1</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>Header 2</hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
    <hp:tr>
        <hp:tc><hp:p><hp:run><hp:t>Row 1 Col 1</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>Row 1 Col 2</hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
</hp:tbl>
"""

root = etree.fromstring(xml_str.encode('utf-8'))

# Find all rows
rows = root.findall(f".//{_HP_NS}tr")
print(f"Original row count: {len(rows)}")

last_row = rows[-1]

# Deep copy the last row
new_row = copy.deepcopy(last_row)

# Append right after the last row
last_row.addnext(new_row)

# Print modified XML
print("Modified XML:")
print(etree.tostring(root, encoding="unicode"))
