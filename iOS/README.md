## Screenshot App — iOS native MVP

SwiftUI app targeting iOS 16+. Open this folder in Xcode, select an iPhone Simulator, and run. The UI supports Photos and Files import with accessible status feedback for processing, completed, duplicate and failed states.

This commit intentionally does not invent an API client: the repository has no HTTP backend contract/base URL yet. The import state machine is local UI scaffolding and must be replaced by the real upload/status client before device acceptance.

For a signed device build, select the app target in Xcode, set a unique bundle identifier and Apple Development team, connect a trusted iPhone, then Build & Run. A paid Apple Developer account is required for external TestFlight distribution.
