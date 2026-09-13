import Foundation
public enum ImportStatus: String, CaseIterable, Identifiable { case processing, completed, duplicate, failed; public var id: String { rawValue }; var label: String { rawValue.capitalized } }
public struct ImportItem: Identifiable, Equatable { public let id = UUID(); public let name: String; public let size: String; public var status: ImportStatus; public let preservation: String }
@MainActor public final class ImportViewModel: ObservableObject {
    @Published public private(set) var items: [ImportItem] = []; @Published public private(set) var isProcessing = false
    public init() {}
    public func add(names: [String]) { guard !names.isEmpty else { return }; isProcessing = true; items += names.map { ImportItem(name: $0, size: "Original", status: .processing, preservation: "Original locked") }; Task { @MainActor in try? await Task.sleep(for: .milliseconds(450)); items = items.map { item in var copy = item; if item.status == .processing { copy.status = item.name.localizedCaseInsensitiveContains("duplicate") ? .duplicate : .completed }; return copy }; isProcessing = false } }
}
