import os
import shutil
import uuid

from ..core.config import settings
from ..domain.models import HwpxBlock, HwpxReadResponse
from ..infra.hwpx_tool import HwpxTool


class EditorService:
    def __init__(self):
        self.tool = HwpxTool()

    def process_read_request(self, file_path: str, original_filename: str) -> HwpxReadResponse:
        """Reads HWPX and returns the flattened blocks."""
        # Create a unique temp directory for this extraction
        session_id = str(uuid.uuid4())
        session_dir = os.path.join(settings.TEMP_DIR, session_id)

        blocks: list[HwpxBlock] = []
        try:
            # 1. Extract
            extracted_path = self.tool.extract_hwpx(file_path, session_dir)

            # 2. Find Contents/section*.xml files
            contents_dir = os.path.join(extracted_path, "Contents")
            if not os.path.exists(contents_dir):
                raise ValueError("Invalid HWPX format: Contents directory not found.")

            section_files = [
                f
                for f in os.listdir(contents_dir)
                if f.startswith("section") and f.endswith(".xml")
            ]

            # Sort by section number (section0.xml, section1.xml, ...)
            section_files.sort(key=lambda x: int(x.replace("section", "").replace(".xml", "")))

            # 3. Iterate blocks
            for sec_file in section_files:
                sec_idx = int(sec_file.replace("section", "").replace(".xml", ""))
                sec_path = os.path.join(contents_dir, sec_file)

                for block in self.tool.iter_blocks(sec_path, section_idx=sec_idx):
                    blocks.append(HwpxBlock(**block))

        finally:
            # 4. Cleanup
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)

        return HwpxReadResponse(file_name=original_filename, blocks=blocks)

    def process_modify_request(
        self, file_path: str, modifications: list[dict], output_filepath: str
    ) -> str:
        """Extracts HWPX, applies modifications, and packages it back."""
        session_id = str(uuid.uuid4())
        session_dir = os.path.join(settings.TEMP_DIR, session_id)

        try:
            # 1. Extract
            extracted_path = self.tool.extract_hwpx(file_path, session_dir)
            contents_dir = os.path.join(extracted_path, "Contents")

            if not os.path.exists(contents_dir):
                raise ValueError("Invalid HWPX format: Contents directory not found.")

            # 2. Group modifications by section
            # Currently we only parse section0.xml, but this logic can scale
            section_mods: dict[int, list[dict]] = {}
            for mod in modifications:
                # "sec0_p1" -> "sec0"
                parts = mod["block_id"].split("_")
                sec_id = parts[0] if parts[0].startswith("sec") else "sec0"
                sec_idx = int(sec_id.replace("sec", ""))

                if sec_idx not in section_mods:
                    section_mods[sec_idx] = []
                section_mods[sec_idx].append(mod)

            # 3. Apply modifications to each section
            for sec_idx, mods in section_mods.items():
                sec_path = os.path.join(contents_dir, f"section{sec_idx}.xml")
                if os.path.exists(sec_path):
                    self.tool.apply_modifications(sec_path, mods, section_idx=sec_idx)

            # 4. Package back to the output path
            self.tool.package_hwpx(extracted_path, output_filepath)

        finally:
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)

        return output_filepath
