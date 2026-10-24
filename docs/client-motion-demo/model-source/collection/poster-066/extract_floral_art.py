"""Recover only the printed watercolor colour mask; preserve the original flower positions."""
from pathlib import Path
import numpy as np
from PIL import Image
out=Path(__file__).resolve().parent;client=out.parents[2]
im=Image.open(client.parent/'mobile-client-preview/assets/posters/poster-066.webp').convert('RGB').crop((738,468,1094,814))
a=np.asarray(im).astype(float);chroma=a.max(2)-a.min(2);alpha=np.clip((chroma-20)/16,0,1)
# Black lettering is recreated from the approved vector wordmark, never left under it.
alpha[(a.max(2)<185)&(chroma<65)]=0
rgba=np.dstack((a,alpha*255)).astype('uint8');Image.fromarray(rgba).save(out/'floral.png')
