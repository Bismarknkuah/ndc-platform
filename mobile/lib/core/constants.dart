/// Central place for environment-specific configuration.
///
/// Point this at your running backend. For the Docker Compose setup in
/// the `ndc-backend` project this is http://localhost:8000 on a desktop
/// emulator, or http://10.0.2.2:8000 on the standard Android emulator
/// (which cannot resolve "localhost" as the host machine).
class AppConfig {
  AppConfig._();

  static const String apiBaseUrl = String.fromEnvironment(
    'NDC_API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );
}
