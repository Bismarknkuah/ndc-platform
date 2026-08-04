import 'package:flutter/foundation.dart';

import '../../core/api_client.dart';
import '../../core/secure_storage.dart';
import '../../models/user.dart';

enum AuthStatus { unknown, authenticated, unauthenticated }

/// Single source of truth for whether the app has a valid session. The app
/// root listens to this to decide whether to show the login flow or the
/// main app shell.
class AuthProvider extends ChangeNotifier {
  AuthStatus status = AuthStatus.unknown;
  NdcUser? currentUser;
  String? lastError;
  bool isBusy = false;

  Future<void> restoreSession() async {
    final hasSession = await TokenStorage.instance.hasSession;
    if (!hasSession) {
      status = AuthStatus.unauthenticated;
      notifyListeners();
      return;
    }
    try {
      final response = await ApiClient.instance.get('/auth/me/');
      currentUser = NdcUser.fromJson(response);
      status = AuthStatus.authenticated;
    } catch (_) {
      await TokenStorage.instance.clear();
      status = AuthStatus.unauthenticated;
    }
    notifyListeners();
  }

  Future<bool> login({required String email, required String password}) async {
    isBusy = true;
    lastError = null;
    notifyListeners();

    try {
      final response = await ApiClient.instance.post(
        '/auth/login/',
        data: {'email': email, 'password': password},
      );
      final tokens = response['tokens'] as Map<String, dynamic>;
      await TokenStorage.instance.saveTokens(
        accessToken: tokens['access'] as String,
        refreshToken: tokens['refresh'] as String,
      );
      currentUser = NdcUser.fromJson(response['user'] as Map<String, dynamic>);
      status = AuthStatus.authenticated;
      return true;
    } on ApiException catch (error) {
      lastError = error.message;
      status = AuthStatus.unauthenticated;
      return false;
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    final refreshToken = await TokenStorage.instance.refreshToken;
    if (refreshToken != null) {
      try {
        await ApiClient.instance.post(
          '/auth/logout/',
          data: {'refresh': refreshToken},
        );
      } catch (_) {
        // Best-effort server-side revocation; clear local session regardless.
      }
    }
    await TokenStorage.instance.clear();
    currentUser = null;
    status = AuthStatus.unauthenticated;
    notifyListeners();
  }
}
