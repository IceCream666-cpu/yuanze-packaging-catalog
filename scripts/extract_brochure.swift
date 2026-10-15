// Read-only PDF rendering and OCR. Keeps page coordinates and original page images.
import Foundation
import PDFKit
import AppKit
import Vision
let source=URL(fileURLWithPath:CommandLine.arguments[1])
let output=URL(fileURLWithPath:CommandLine.arguments[2])
try FileManager.default.createDirectory(at:output,withIntermediateDirectories:true)
guard let document=PDFDocument(url:source) else {fatalError("Unable to open PDF")}
for index in 0..<document.pageCount {
 let name=String(format:"%04d",index+1)
 let target=output.appendingPathComponent(name+".json")
 if FileManager.default.fileExists(atPath:target.path){continue}
 try autoreleasepool {
  guard let page=document.page(at:index) else {throw NSError(domain:"PageMissing",code:1)}
  let b=page.bounds(for:.mediaBox),ratio=2000/max(b.width,b.height)
  let image=page.thumbnail(of:CGSize(width:b.width*ratio,height:b.height*ratio),for:.mediaBox)
  var rect=NSRect(origin:.zero,size:image.size)
  guard let cg=image.cgImage(forProposedRect:&rect,context:nil,hints:nil) else {throw NSError(domain:"Render",code:2)}
  let request=VNRecognizeTextRequest()
  request.recognitionLevel = .accurate
  request.recognitionLanguages=["zh-Hans","en-US"]
  request.usesLanguageCorrection=false
  request.minimumTextHeight=0.003
  try VNImageRequestHandler(cgImage:cg,options:[:]).perform([request])
  let lines:[[String:Any]]=(request.results ?? []).compactMap {observation in
   guard let text=observation.topCandidates(1).first else{return nil}
   let b=observation.boundingBox
   return ["text":text.string,"confidence":text.confidence,"bbox":[b.minX,1-b.maxY,b.width,b.height]]
  }
  let bitmap=NSBitmapImageRep(cgImage:cg)
  guard let jpeg=bitmap.representation(using:.jpeg,properties:[.compressionFactor:0.92]) else {throw NSError(domain:"Encode",code:3)}
  try jpeg.write(to:output.appendingPathComponent(name+".jpg"),options:.atomic)
  let data:[String:Any]=["page":index+1,"width":cg.width,"height":cg.height,"lines":lines,"nativeText":page.string ?? ""]
  try JSONSerialization.data(withJSONObject:data,options:[.prettyPrinted,.sortedKeys]).write(to:target,options:.atomic)
  print("Extracted \(index+1)/\(document.pageCount)");fflush(stdout)
 }
}
