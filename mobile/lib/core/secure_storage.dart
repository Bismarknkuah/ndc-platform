import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Thin wrapper around flutter_secure_storage for the two JWTs the
/// backend issues. Kept as a single class so the rest of the app never
/// touches the storage package directly.
class TokenStorage {
  TokenStorage._();

  static const TokenStorage instance = TokenStorage._();

  static const _storage = FlutterSecureStorage();
  static const _accessKey = 'ndc_access_token';
  static const _refreshKey = 'ndc_refresh_token';

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _storage.write(key: _accessKey, value: accessToken);
    await _storage.write(key: _refreshKey, value: refreshToken);
  }

  Future<String?> get accessToken => _storage.read(key: _accessKey);

  Future<String?> get refreshToken => _storage.read(key: _refreshKey);

  Future<void> updateAccessToken(String accessToken) async {
    await _storage.write(key: _accessKey, value: accessToken);
  }

  Future<void> clear() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }

  Future<bool> get hasSession async => (await accessToken) != null;
}
