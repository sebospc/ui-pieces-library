// Usage: vision_text <image.png>
// Prints one JSON array: each recognised text line with its box in pixels, origin top-left.
// Apple's boxes are approximate; measure.py measures the ink inside them itself.
import Foundation
import ImageIO
import Vision

struct Line: Encodable {
    let text: String
    let confidence: Float
    let box: [Double]  // x, y, width, height
}

let path = CommandLine.arguments[1]
guard let source = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
      let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
    FileHandle.standardError.write("cannot read \(path)\n".data(using: .utf8)!)
    exit(1)
}
let width = Double(image.width), height = Double(image.height)

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false  // keep numbers and short labels as drawn
try VNImageRequestHandler(cgImage: image).perform([request])

let lines: [Line] = (request.results ?? []).compactMap { observation in
    guard let best = observation.topCandidates(1).first else { return nil }
    let box = observation.boundingBox  // normalised, origin bottom-left
    return Line(text: best.string, confidence: best.confidence,
                box: [box.minX * width, (1 - box.maxY) * height, box.width * width, box.height * height])
}
let json = try JSONEncoder().encode(lines)
print(String(data: json, encoding: .utf8)!)
