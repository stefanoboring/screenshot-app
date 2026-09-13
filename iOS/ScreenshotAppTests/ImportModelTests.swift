import XCTest
@testable import ScreenshotApp
@MainActor final class ImportModelTests: XCTestCase { func testOriginalIsLocked() { let model = ImportViewModel(); model.add(names: ["one.png"]); XCTAssertEqual(model.items.first?.preservation, "Original locked"); XCTAssertTrue(model.isProcessing) } }
