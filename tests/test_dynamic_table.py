import os

from app.infra.hwpx_tool import HwpxTool


def test_dynamic_table_expansion():
    tool = HwpxTool()
    template_path = "../templates/공문 예시.hwpx"
    temp_dir = "../temp_hwpx"

    result_dir = "../result"
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    output_path = os.path.join(result_dir, "완성본_동적테이블테스트.hwpx")

    print(f"Extracting {template_path}...")
    extracted_path = tool.extract_hwpx(template_path, temp_dir)

    section_xml_path = os.path.join(extracted_path, "Contents", "section0.xml")

    # Let's inspect what tables exist first
    print("Reading blocks...")
    blocks = list(tool.iter_blocks(section_xml_path))
    tbl_blocks = [b for b in blocks if "tbl" in b["block_id"]]

    # We don't know exactly how many rows are in the template tables right now
    # But let's assume tbl0 has at least 1 row (r0).
    # We will submit a modification for an out-of-bounds row (e.g. r5)

    if not tbl_blocks:
        print("No tables found in the template. Test aborted.")
        return

    first_tbl_block = tbl_blocks[0]
    # Extract the target_text of this block so we can match it in our duplication payload
    base_target_text = first_tbl_block["text"]

    print(f"First table cell found: {first_tbl_block['block_id']}, Text: '{base_target_text}'")

    # Let's see max row currently
    current_max_r = 0
    base_prefix = first_tbl_block["block_id"].split("_r")[0]  # sec0_tbl0
    for b in tbl_blocks:
        if b["block_id"].startswith(base_prefix):
            r = int(b["block_id"].split("_r")[1].split("_c")[0])
            current_max_r = max(current_max_r, r)

    print(f"Current max row for {base_prefix}: {current_max_r}")

    # Create request exceeding current max
    new_r = current_max_r + 3  # add 3 rows at least

    modifications = [
        {
            "block_id": f"{base_prefix}_r{new_r}_c0",
            "target_text": base_target_text,  # Assuming the template text doesn't change
            "replace_text": "THIS IS A DYNAMICALLY GENERATED ROW",
        }
    ]

    print(f"Applying modifications: {modifications}")
    tool.apply_modifications(section_xml_path, modifications)

    print(f"Packaging back to {output_path}...")
    tool.package_hwpx(extracted_path, output_path)
    print("Done! Open 완성본_동적테이블테스트.hwpx in Hancom to verify.")


if __name__ == "__main__":
    test_dynamic_table_expansion()
