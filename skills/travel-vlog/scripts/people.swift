// people.swift: find people and faces in still images with Apple Vision (macOS, offline, no model download).
// Usage: swift people.swift <image>...   Prints one JSON line per image:
// {"image": "...", "people": [[x, y, w, h], ...], "faces": [[x, y, w, h], ...]}  boxes 0-1, origin top-left.
import Foundation
import Vision

func boxes(_ results: [VNObservation]?, _ minConfidence: Float) -> [[Double]] {
    (results ?? []).compactMap { $0 as? VNDetectedObjectObservation }
        .filter { $0.confidence >= minConfidence }
        .map { o in
            let b = o.boundingBox
            return [b.minX, 1 - b.maxY, b.width, b.height].map { (Double($0) * 1000).rounded() / 1000 }
        }
}

for path in CommandLine.arguments.dropFirst() {
    let url = URL(fileURLWithPath: path)
    let humans = VNDetectHumanRectanglesRequest()
    humans.upperBodyOnly = false
    let faces = VNDetectFaceRectanglesRequest()
    let handler = VNImageRequestHandler(url: url, options: [:])
    var out: [String: Any] = ["image": path]
    do {
        try handler.perform([humans, faces])
        out["people"] = boxes(humans.results, 0.3)
        out["faces"] = boxes(faces.results, 0.5)
    } catch {
        out["error"] = "\(error)"
    }
    let data = try! JSONSerialization.data(withJSONObject: out, options: [.sortedKeys])
    print(String(data: data, encoding: .utf8)!)
}
