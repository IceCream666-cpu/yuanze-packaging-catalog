// Native bitmap decode/canvas are browser I/O boundaries in jsdom. Use real
// bounded PNG files and record the actual module's draw/encode operations.
const zlib=require('node:zlib');
function crc32(bytes){let c=0xffffffff;for(const b of bytes){c^=b;for(let n=0;n<8;n++)c=(c>>>1)^((c&1)?0xedb88320:0);}return (c^0xffffffff)>>>0;}
function chunk(type,data){const kind=Buffer.from(type),size=Buffer.alloc(4),crc=Buffer.alloc(4);size.writeUInt32BE(data.length);crc.writeUInt32BE(crc32(Buffer.concat([kind,data])));return Buffer.concat([size,kind,data,crc]);}
function png(width=320,height=640){
  const header=Buffer.alloc(13);header.writeUInt32BE(width,0);header.writeUInt32BE(height,4);header[8]=8;header[9]=6;
  const row=Buffer.alloc(width*4+1,255);row[0]=0;const raster=Buffer.alloc(row.length*height);for(let y=0;y<height;y++)row.copy(raster,y*row.length);
  return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),chunk('IDAT',zlib.deflateSync(raster)),chunk('IEND',Buffer.alloc(0))]);
}
function pictureFile(w,name='camera.png',{width=320,height=640,type='image/png'}={}){return new w.File([png(width,height)],name,{type});}
function installImageBrowser(w,{decodeDelay=0,dimensions=null,broken=false}={}){
  const operations=[];
  w.Image=class {
    set src(value){this._src=value;if(!value)return;setTimeout(()=>{
      if(this._src!==value)return;
      const binary=Buffer.from(value.split(',')[1]||'','base64');
      const size=dimensions||{width:binary[0]===137?binary.readUInt32BE(16):800,height:binary[0]===137?binary.readUInt32BE(20):1200};
      this.naturalWidth=size.width;this.naturalHeight=size.height;
      if(broken)this.onerror?.();else this.onload?.();
    },decodeDelay);}
    get src(){return this._src;}
  };
  w.HTMLCanvasElement.prototype.getContext=function(){
    const canvas=this;if(!canvas._context)canvas._context={
      fillStyle:'',strokeStyle:'',lineWidth:0,
      fillRect(...args){operations.push({type:'fill',style:this.fillStyle,args,width:canvas.width,height:canvas.height});},
      drawImage(...args){operations.push({type:'draw',args,width:canvas.width,height:canvas.height});},
      strokeRect(...args){operations.push({type:'stroke',args});},
      translate(...args){operations.push({type:'translate',args});},rotate(...args){operations.push({type:'rotate',args});},
    };return canvas._context;
  };
  w.HTMLCanvasElement.prototype.toDataURL=function(type,quality){operations.push({type:'encode',mime:type,quality,width:this.width,height:this.height});return 'data:'+type+';base64,'+Buffer.from([255,216,255,224,0,10]).toString('base64');};
  w.HTMLCanvasElement.prototype.setPointerCapture=function(){};w.HTMLCanvasElement.prototype.hasPointerCapture=()=>false;
  return operations;
}
module.exports={png,pictureFile,installImageBrowser};
