import os
import zipfile
from typing import Iterator, Dict, Any, List
from lxml import etree

_HP_NS = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
_SEC_NS = "{http://www.hancom.co.kr/hwpml/2011/section}"

class HwpxTool:
    def extract_hwpx(self, file_path: str, temp_dir: str) -> str:
        """Extracts HWPX file to a temporary directory."""
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
        
        extract_path = os.path.join(temp_dir, os.path.basename(file_path) + "_extracted")
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        return extract_path

    def package_hwpx(self, extracted_path: str, output_path: str) -> None:
        """Packages the extracted directory back into a HWPX (ZIP) file."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for root, dirs, files in os.walk(extracted_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, extracted_path)
                    zip_ref.write(file_path, arcname)

    def _get_element_text(self, element: etree._Element) -> str:
        """Extracts text from all <hp:t> child nodes."""
        text_parts = []
        for t_node in element.findall(f".//{_HP_NS}t"):
            if t_node.text:
                text_parts.append(t_node.text)
        return "".join(text_parts).strip()

    def iter_blocks(self, section_xml_path: str, section_idx: int = 0) -> Iterator[Dict[str, Any]]:
        """Parses XML and yields blocks with semantic block_ids."""
        tree = etree.parse(section_xml_path)
        root = tree.getroot()
        
        p_idx = 0
        tbl_idx = 0
        
        # In section0.xml, paragraphs are direct children of <sec>
        for p_elem in root.findall(f"./{_HP_NS}p"):
            # A paragraph might just be text, or it might contain a table
            has_table = False
            for tbl_elem in p_elem.findall(f".//{_HP_NS}tbl"):
                has_table = True
                r_idx = 0
                for tr_elem in tbl_elem.findall(f".//{_HP_NS}tr"):
                    c_idx = 0
                    for tc_elem in tr_elem.findall(f".//{_HP_NS}tc"):
                        text = self._get_element_text(tc_elem)
                        yield {
                            "block_id": f"sec{section_idx}_tbl{tbl_idx}_r{r_idx}_c{c_idx}",
                            "type": "table_cell",
                            "text": text
                        }
                        c_idx += 1
                    r_idx += 1
                tbl_idx += 1
            
            # Yield the paragraph block if it has text (we might skip empty ones to reduce noise, but let's yield if it has text)
            # We should be careful to only extract text that is NOT inside a table cell if the paragraph contains a table.
            # But usually, if a paragraph contains a table, its own text is minimal or just the table locator.
            # Let's extract paragraph text by excluding text inside tables.
            p_text = ""
            if not has_table:
                p_text = self._get_element_text(p_elem)
            else:
                # Need to get text only from <hp:run> elements that are direct children of this <hp:p>, 
                # but NOT those inside the table.
                # Since we want to simplify, we can just extract all text but tables have their own text. 
                # Let's write a simple exclusion:
                text_parts = []
                for run_elem in p_elem.findall(f"./{_HP_NS}run"):
                    if run_elem.find(f".//{_HP_NS}tbl") is None:
                        text_parts.append(self._get_element_text(run_elem))
                p_text = "".join(text_parts).strip()
            
            if p_text:
                yield {
                    "block_id": f"sec{section_idx}_p{p_idx}",
                    "type": "paragraph",
                    "text": p_text
                }
            p_idx += 1

    def _distribute_lengths(self, new_total: int, original_weights: List[int]) -> List[int]:
        """Distributes the new total length across the original weights using the largest remainder method."""
        if not original_weights:
            return []
            
        sum_weights = sum(original_weights)
        if sum_weights == 0:
            # If original weights were 0, just distribute evenly
            n = len(original_weights)
            base = new_total // n
            rem = new_total % n
            return [base + 1 if i < rem else base for i in range(n)]
            
        # Calculate exactly and get floor amount
        exact = [(new_total * w) / sum_weights for w in original_weights]
        result = [int(x) for x in exact]
        remainders = [exact[i] - result[i] for i in range(len(original_weights))]
        
        # Distribute the remaining length
        diff = new_total - sum(result)
        # Sort by remainder in descending order
        indexed_remainders = sorted(enumerate(remainders), key=lambda x: x[1], reverse=True)
        
        for i in range(diff):
            idx = indexed_remainders[i][0]
            result[idx] += 1
            
        return result

    def _set_xml_run_text(self, t_node: etree._Element, new_text: str):
        """Sets the text of a <hp:t> node safely."""
        t_node.text = new_text

    def _replace_across_xml_runs(self, t_nodes: List[etree._Element], find_text: str, replace_text: str) -> int:
        """Finds and replaces texts across fragmented <hp:t> XML nodes while preserving tags."""
        if not t_nodes:
            return 0
            
        # 1. Merge all text
        texts = [t.text if t.text else "" for t in t_nodes]
        merged = "".join(texts)
        
        if find_text not in merged:
            return 0
            
        # 2. Replace in merged text
        new_merged = merged.replace(find_text, replace_text)
        
        # 3. Calculate weights (original lengths)
        weights = [len(text) for text in texts]
        
        # 4. Redistribute new lengths preserving the weight distribution
        redistributed = self._distribute_lengths(len(new_merged), weights)
        
        # 5. Write back to nodes
        cursor = 0
        for t_node, size in zip(t_nodes, redistributed):
            self._set_xml_run_text(t_node, new_merged[cursor : cursor + size])
            cursor += size
            
        return merged.count(find_text)

    def apply_modifications(self, section_xml_path: str, modifications: List[Dict[str, str]], section_idx: int = 0) -> None:
        """Applies text modifications to the target Block IDs in the XML."""
        tree = etree.parse(section_xml_path)
        root = tree.getroot()
        
        mod_map = {mod["block_id"]: mod for mod in modifications}
        
        p_idx = 0
        tbl_idx = 0
        
        for p_elem in root.findall(f"./{_HP_NS}p"):
            has_table = False
            for tbl_elem in p_elem.findall(f".//{_HP_NS}tbl"):
                has_table = True
                r_idx = 0
                for tr_elem in tbl_elem.findall(f".//{_HP_NS}tr"):
                    c_idx = 0
                    for tc_elem in tr_elem.findall(f".//{_HP_NS}tc"):
                        block_id = f"sec{section_idx}_tbl{tbl_idx}_r{r_idx}_c{c_idx}"
                        if block_id in mod_map:
                            mod = mod_map[block_id]
                            t_nodes = tc_elem.findall(f".//{_HP_NS}t")
                            self._replace_across_xml_runs(t_nodes, mod["target_text"], mod["replace_text"])
                        c_idx += 1
                    r_idx += 1
                tbl_idx += 1
                
            block_id = f"sec{section_idx}_p{p_idx}"
            if not has_table and block_id in mod_map:
                 mod = mod_map[block_id]
                 # We only get texts outside of tables here since has_table is False.
                 # If a paragraph has a table we shouldn't attempt modifying paragraph texts since it's handled above / skipped
                 t_nodes = p_elem.findall(f".//{_HP_NS}t")
                 self._replace_across_xml_runs(t_nodes, mod["target_text"], mod["replace_text"])
                 
            p_idx += 1
            
        # Write the modified tree back
        tree.write(section_xml_path, encoding="utf-8", xml_declaration=True)
