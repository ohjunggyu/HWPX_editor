import xml.etree.ElementTree as ET
import xml.dom.minidom

def pretty_print_xml(filepath, output_filepath):
    try:
        tree = ET.parse(filepath)
        xml_string = ET.tostring(tree.getroot(), encoding='utf-8')
        parsed = xml.dom.minidom.parseString(xml_string)
        pretty_xml = parsed.toprettyxml(indent="  ")
        
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
        print(f"Successfully formatted XML to {output_filepath}")
    except Exception as e:
        print(f"Error formatting XML: {e}")

if __name__ == "__main__":
    pretty_print_xml("hwpx_temp/Contents/section0.xml", "hwpx_temp/Contents/section0_pretty.xml")
