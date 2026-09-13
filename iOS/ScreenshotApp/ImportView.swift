import SwiftUI
import PhotosUI

public struct ImportView: View {
    @StateObject private var model = ImportViewModel()
    @State private var selectedPhotos: [PhotosPickerItem] = []
    @State private var showFiles = false

    public init() {}

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    header
                    privacyNote
                    importCard
                    if !model.items.isEmpty { itemList }
                    reviewNote
                }
                .padding(.horizontal, 20).padding(.vertical, 24)
            }
            .background(Color.gray.opacity(0.08).ignoresSafeArea())
            .toolbar { ToolbarItem(placement: .principal) { Text("Screenshot App").font(.headline) } }
        }
        .onChange(of: selectedPhotos) { items in
            model.add(names: items.enumerated().map { "Photo \($0.offset + 1)" })
        }
        .fileImporter(isPresented: $showFiles, allowedContentTypes: [.image], allowsMultipleSelection: true) { result in
            if case .success(let urls) = result { model.add(names: urls.map(\.lastPathComponent)) }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("LIBRARY / IMPORT").font(.caption.bold()).tracking(1.2).foregroundStyle(.purple)
            Text("Bring your screenshots into focus.").font(.system(size: 34, weight: .bold, design: .rounded))
            Text("Add a batch and we’ll preserve the originals while preparing searchable, reviewable records.").foregroundStyle(.secondary)
        }
    }

    private var privacyNote: some View { Label("Private by default\nEvidence and sensitive content stay out of ordinary views.", systemImage: "lock.shield.fill").font(.subheadline).foregroundStyle(.indigo).padding().frame(maxWidth: .infinity, alignment: .leading).background(Color.indigo.opacity(0.1), in: RoundedRectangle(cornerRadius: 14)) }

    private var importCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack { VStack(alignment: .leading) { Text("Import batch").font(.title3.bold()); Text("PNG, JPG, HEIC or WEBP · up to 50 files").font(.subheadline).foregroundStyle(.secondary) }; Spacer(); Text(model.isProcessing ? "Processing" : "Ready").font(.caption.bold()).foregroundStyle(model.isProcessing ? .purple : .green).padding(.horizontal, 10).padding(.vertical, 6).background(.thinMaterial, in: Capsule()) }
            VStack(spacing: 10) {
                Image(systemName: "arrow.up.circle").font(.largeTitle).foregroundStyle(.purple)
                Text("Select screenshots").font(.headline)
                Text("or choose files from this device").font(.subheadline).foregroundStyle(.secondary)
                HStack { PhotosPicker(selection: $selectedPhotos, maxSelectionCount: 50, matching: .images) { Label("Choose from Photos", systemImage: "photo.on.rectangle") }.buttonStyle(.borderedProminent); Button("Files", systemImage: "folder") { showFiles = true }.buttonStyle(.bordered) }
            }.frame(maxWidth: .infinity).padding(.vertical, 24).background(Color.purple.opacity(0.06), in: RoundedRectangle(cornerRadius: 14)).accessibilityElement(children: .contain)
        }.padding(18).background(.background, in: RoundedRectangle(cornerRadius: 18)).shadow(color: .black.opacity(0.06), radius: 12, y: 4)
    }

    private var itemList: some View {
        VStack(alignment: .leading, spacing: 10) { Text("Imported screenshots").font(.title3.bold()); ForEach(model.items) { item in HStack { VStack(alignment: .leading) { Text(item.name).font(.headline); Text("\(item.size) · \(item.preservation)").font(.caption).foregroundStyle(.secondary) }; Spacer(); Text(item.status.label).font(.caption.bold()).padding(.horizontal, 9).padding(.vertical, 6).background(statusColor(item.status).opacity(0.14), in: Capsule()).foregroundStyle(statusColor(item.status)) }.padding(.vertical, 5) } }
    }

    private var reviewNote: some View { Label("Some items may need your review\nLow-confidence classifications and sensitive evidence are never silently filed.", systemImage: "exclamationmark.triangle.fill").font(.subheadline).foregroundStyle(.orange).padding().frame(maxWidth: .infinity, alignment: .leading).background(Color.orange.opacity(0.1), in: RoundedRectangle(cornerRadius: 14)) }
    private func statusColor(_ status: ImportStatus) -> Color { status == .completed ? .green : status == .duplicate ? .orange : status == .failed ? .red : .purple }
}
