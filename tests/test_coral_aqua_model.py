"""Check the exported Coral & Aqua jar against the visible reference proportions."""
import unittest
import xml.etree.ElementTree as ET
from test_micro_cream_model import ExportedModelReader, CLIENT

class CoralAquaModelTests(ExportedModelReader):
    model_id='poster-013'
    body_name='Rounded-square hollow clear jar'

    def test_proportions_and_empty_hollow_container(self):
        width=self.width()
        low,high=self.bounds([p for n in self.mesh_names() for p in self.positions(n)])
        self.assertAlmostEqual(high[1]-low[1],2.9,delta=.002)
        self.assertAlmostEqual((high[1]-low[1])/width,1.075,delta=.002)
        low,high=self.bounds(self.positions(self.body_name))
        self.assertAlmostEqual((high[2]-low[2])/width,.9,delta=.002)
        hits=self.ray_intersections(self.body_name)
        self.assertAlmostEqual(max(hits)/width,.07,delta=.002)
        self.assertEqual(self.material(self.body_name)['extensions']['KHR_materials_transmission']['transmissionFactor'],1)

    def test_complete_print_and_colour_border_move_off_blank_paper(self):
        source=CLIENT/'model-source/collection'/self.model_id
        paper=ET.parse(source/'label.svg').getroot()
        self.assertFalse(any(e.tag.endswith(('}text','}path')) for e in paper.iter()))
        printing=ET.parse(source/'print.svg').getroot()
        self.assertEqual([e.text for e in printing.iter() if e.tag.endswith('}text')],['BEACH MAGIC','SUGAR SCRUB'])
        self.assertEqual(len([e for e in printing.iter() if e.tag.endswith('}path')]),3)
        self.assertEqual(self.ancestor('Complete logo name and two-colour border'),'LogoPrint')
        self.assertEqual(self.ancestor('Blank warm cream paper label'),'PaperLabel')
        self.assertEqual({self.nodes[i]['name'] for i in self.gltf['scenes'][0]['nodes']},{'Body','Closure','InnerLid','PaperLabel','LogoPrint'})

if __name__=='__main__':unittest.main()
