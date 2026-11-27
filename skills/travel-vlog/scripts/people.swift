// people.swift: find people, faces, text and salient objects in still images with Apple Vision (macOS, offline,
// no model download). Usage: swift people.swift <image>...   Prints one JSON line per image:
// {"image": "...", "people": [[x, y, w, h], ...], "faces": [...], "text": [{"box": [...], "text": "..."}],
//  "objects": [...]}  boxes 0-1, origin top-left.
import Foundation
import Vision

func box(_ b: CGRect) -> [Double] {
    [b.minX, 1 - b.maxY, b.width, b.height].map { (Double($0) * 1000).rounded() / 1000 }
}

func boxes(_ results: [VNObservation]?, _ minConfidence: Float) -> [[Double]] {
    (results ?? []).compactMap { $0 as? VNDetectedObjectObservation }
        .filter { $0.confidence >= minConfidence }
        .map { box($0.boundingBox) }
}

for path in CommandLine.arguments.dropFirst() {
    let url = URL(fileURLWithPath: path)
    let humans = VNDetectHumanRectanglesRequest()
    humans.upperBodyOnly = false
    let faces = VNDetectFaceRectanglesRequest()
    let text = VNRecognizeTextRequest()
    text.recognitionLevel = .fast
    text.recognitionLanguages = ["en-US", "zh-Hant"]
    let salient = VNGenerateObjectnessBasedSaliencyImageRequest()
    let handler = VNImageRequestHandler(url: url, options: [:])
    var out: [String: Any] = ["image": path]
    do {
        try handler.perform([humans, faces, text, salient])
        out["people"] = boxes(humans.results, 0.3)
        out["faces"] = boxes(faces.results, 0.5)
        out["text"] = (text.results ?? []).filter { $0.confidence >= 0.5 }.compactMap { o -> [String: Any]? in
            guard let s = o.topCandidates(1).first?.string, s.count >= 2 else { return nil }
            return ["box": box(o.boundingBox), "text": s]
        }
        out["objects"] = (salient.results?.first?.salientObjects ?? []).map { box($0.boundingBox) }
    } catch {
        out["error"] = "\(error)"
    }
    let data = try! JSONSerialization.data(withJSONObject: out, options: [.sortedKeys])
    print(String(data: data, encoding: .utf8)!)
}
