import csv
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
import pilot_pipeline as pp


class PilotTests(unittest.TestCase):
    def test_cosine_not_raw_dot_and_stable_ties(self):
        ids, scores = pp.ranking([[100, 100], [1, 0], [2, 0]], [[5, 0]], 3)
        self.assertEqual(ids.tolist(), [1, 2, 0])
        np.testing.assert_allclose(scores, [1, 1, 2**-0.5], atol=1e-6)

    def test_invalid_embeddings(self):
        for v in ([[0, 0]], [[float('nan'), 1]], [1, 2]):
            with self.assertRaises(ValueError): pp.normalized(v)
        with self.assertRaises(ValueError): pp.ranking([[1, 2]], [[1, 2, 3]], 1)

    def test_session2_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'sources.csv'
            path.write_text('session_id,camera_id,path\nsession2,cam01,clip.mp4\n')
            with self.assertRaises(ValueError): pp.sources({'sources':str(path)})

    def test_index_search_contract_with_controlled_models(self):
        """Real M3 crop and file outputs; detector/encoder are controlled doubles.

        Verifies BGR->RGB, metadata alignment, timestamps, cosine and tamper checks.
        Does NOT assert real detector/model accuracy or pilot availability.
        """
        import torch
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = json.loads((pp.ROOT/'configs/LG04-pilot-session1.json').read_text())
            config.update(device='cpu', sources=str(root/'sources.csv'), output=str(root/'index'),
                          weights=str(root/'fake.pt'), embedding_dim=3, padding_ratio=0)
            (root/'fake.pt').write_bytes(b'controlled fixture, not YOLO')
            with (root/'sources.csv').open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['session_id','camera_id','path','timestamp_offset_ms'])
                for i, color in enumerate(('red','green','blue')):
                    Image.new('RGB',(40,60),color).save(root/f'{color}.png')
                    w.writerow(['session1',f'cam{i}',f'{color}.png',1000*i])
            class Detector:
                def __init__(self, config_path): pass
                def detect(self, bgr):
                    h,w=bgr.shape[:2]
                    return [{'bbox_xyxy':[0,0,w,h],'confidence':0.9}]
            class Model:
                def encode_image(self, batch): return batch.mean(dim=(2,3))
                def encode_text(self, tokens): return tokens
            def transform(image):
                return torch.from_numpy(np.asarray(image).copy()).permute(2,0,1).float()/255
            def imdecode(raw, flag):
                import io
                with Image.open(io.BytesIO(raw.tobytes())) as im:
                    return np.asarray(im.convert('RGB'))[:,:,::-1].copy()
            cv2 = types.SimpleNamespace(IMREAD_COLOR=1, COLOR_BGR2RGB=1,
                                        imdecode=imdecode, cvtColor=lambda x, code:x[:,:,::-1].copy())
            original_loader=pp.m3_module
            def load(config, name):
                return types.SimpleNamespace(PersonDetector=Detector) if name=='detector' else original_loader(config,name)
            with patch.dict('sys.modules',{'cv2':cv2}), \
                 patch.object(pp,'preflight',return_value={'ready_for_index':True}), \
                 patch.object(pp,'m3_module',side_effect=load), \
                 patch.object(pp,'encoder',return_value=(Model(),transform,lambda q:torch.tensor([[1.,0.,0.]]))), \
                 patch('importlib.metadata.version',return_value='test-double'):
                config_file=root/'config.json';config_file.write_text(json.dumps(config))
                pp.index(config,config_file)
                output=root/'top.csv'
                pp.search(config,'người mặc áo đỏ',str(output))
                with output.open(encoding='utf-8-sig') as f: ranked=list(csv.DictReader(f))
                self.assertEqual(ranked[0]['camera_id'],'cam0')
                self.assertEqual(float(ranked[0]['cosine']),1)
                self.assertEqual(len(ranked),3)
                gallery=np.load(root/'index/embeddings.npy')
                np.testing.assert_allclose(gallery,np.eye(3),atol=1e-6)
                with (root/'index/candidates.csv').open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
                self.assertEqual([float(r['timestamp_ms']) for r in rows],[0,1000,2000])
                with self.assertRaises(ValueError): pp.index(config,config_file)
                (root/'index/candidates.csv').write_text('modified')
                with self.assertRaises(ValueError): pp.search(config,'query',str(root/'other.csv'))


if __name__=='__main__': unittest.main()
