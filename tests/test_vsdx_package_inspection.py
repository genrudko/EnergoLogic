from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZIP_DEFLATED, ZipFile

from energologic.frontends.visio.legacy_inspection import inspect_legacy_visio
from energologic.frontends.visio.vsdx_package import capture_vsdx_package


PAGES = '''<?xml version="1.0" encoding="UTF-8"?>
<Pages xmlns="http://schemas.microsoft.com/office/visio/2012/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <Page ID="7" NameU="SLD" Name="Схема">
    <PageSheet><Cell N="PageWidth" V="11"/><Cell N="PageHeight" V="8.5"/></PageSheet>
    <Rel r:id="rId1"/>
  </Page>
</Pages>
'''

PAGES_RELS = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="x" Target="page1.xml"/>
</Relationships>
'''

MASTERS = '''<?xml version="1.0" encoding="UTF-8"?>
<Masters xmlns="http://schemas.microsoft.com/office/visio/2012/main">
  <Master ID="42" Name="Старый выключатель" NameU="LegacyCircuitBreaker"/>
</Masters>
'''

PAGE = '''<?xml version="1.0" encoding="UTF-8"?>
<PageContents xmlns="http://schemas.microsoft.com/office/visio/2012/main">
  <PageSheet>
    <Section N="Layer"><Row IX="0"><Cell N="Name" V="35 кВ"/></Row></Section>
  </PageSheet>
  <Shapes>
    <Shape ID="10" Type="Group" Name="QF.10" NameU="QF.10" Master="42">
      <Cell N="PinX" V="2"/><Cell N="PinY" V="5"/><Cell N="Width" V="1"/><Cell N="Height" V="0.6"/><Cell N="LayerMember" V="0"/>
      <Section N="Connection"><Row IX="0"><Cell N="X" V="0.5" F="Width*0.5"/><Cell N="Y" V="0" F="0"/></Row></Section>
      <Section N="Geometry" IX="0"><Row IX="1" T="MoveTo"><Cell N="X" V="0"/><Cell N="Y" V="0"/></Row><Row IX="2" T="LineTo"><Cell N="X" V="1"/><Cell N="Y" V="0.6"/></Row></Section>
      <Text>QF-101</Text>
      <Shapes>
        <Shape ID="11" Type="Shape" NameU="Contact.11" MasterShape="3"><Cell N="PinX" V="2"/><Cell N="PinY" V="5"/><Cell N="Width" V="0.2"/><Cell N="Height" V="0.2"/></Shape>
      </Shapes>
    </Shape>
    <Shape ID="20" Type="Shape" NameU="Connector.20">
      <Cell N="BeginX" V="2" F="PAR(PNT(Sheet.10!Connections.X1,Sheet.10!Connections.Y1))"/><Cell N="BeginY" V="5"/>
      <Cell N="EndX" V="5"/><Cell N="EndY" V="5"/><Cell N="PinX" V="3.5"/><Cell N="PinY" V="5"/><Cell N="Width" V="3"/><Cell N="Height" V="0"/>
      <Section N="Geometry" IX="0"><Row IX="1" T="MoveTo"><Cell N="X" V="0"/><Cell N="Y" V="0"/></Row><Row IX="2" T="LineTo"><Cell N="X" V="3"/><Cell N="Y" V="0"/></Row></Section>
    </Shape>
  </Shapes>
  <Connects><Connect FromSheet="20" FromCell="BeginX" ToSheet="10" ToPart="3"/></Connects>
</PageContents>
'''


def fixture(path: Path) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("visio/pages/pages.xml", PAGES)
        archive.writestr("visio/pages/_rels/pages.xml.rels", PAGES_RELS)
        archive.writestr("visio/pages/page1.xml", PAGE)
        archive.writestr("visio/masters/masters.xml", MASTERS)
        archive.writestr("docProps/app.xml", '<Properties><AppVersion>16.0000</AppVersion></Properties>')


class VsdxPackageInspectionTests(unittest.TestCase):
    def test_package_capture_extracts_real_visio_structure_read_only(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "legacy.vsdx"
            fixture(path)
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            snapshot = capture_vsdx_package(path)
            after = hashlib.sha256(path.read_bytes()).hexdigest()

            self.assertEqual(before, after)
            self.assertTrue(snapshot.read_only)
            self.assertEqual(snapshot.pages[0].page_id, 7)
            self.assertEqual(snapshot.pages[0].width, 11.0)
            self.assertEqual(len(snapshot.pages[0].shapes), 3)
            group, child, connector = snapshot.pages[0].shapes
            self.assertEqual(group.master_name_u, "LegacyCircuitBreaker")
            self.assertEqual(group.layers, ("35 кВ",))
            self.assertEqual(child.parent_shape_id, 10)
            self.assertEqual(child.master_shape_id, 3)
            self.assertEqual(len(group.connection_points), 1)
            self.assertIn("Sheet.10", connector.begin_x_formula)
            self.assertEqual(len(snapshot.pages[0].connects), 1)
            self.assertEqual(snapshot.pages[0].connects[0].to_cell, "ToPart:3")

            report = inspect_legacy_visio(snapshot)
            self.assertEqual(report["statistics"]["page_count"], 1)
            self.assertEqual(report["statistics"]["shape_count"], 3)
            self.assertEqual(report["statistics"]["native_glue_edge_count"], 1)
            self.assertEqual(report["glue_graph"]["edges"][0]["confidence"], "exact_native")


if __name__ == "__main__":
    unittest.main()
