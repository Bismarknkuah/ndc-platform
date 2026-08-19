import 'package:dio/dio.dart';

import 'constants.dart';
import 'secure_storage.dart';

/// Thrown when a request fails, so UI code can show a clean, specific
/// error message rather than a raw exception. Mirrors the backend's
/// {"error": {"code", "message"}} shape.
class ApiException implements Exception {
  ApiException(this.message, {this.code, this.statusCode});

  final String message;
  final String? code;
  final int? statusCode;

  @override
  String toString() => message;
}

/// Thin, app-wide HTTP client. Handles attaching the access token to every
/// request, and transparently refreshing it once on a 401 before retrying
/// the original request - the rest of the app never has to think about
/// tokens at all.
class ApiClient {
  ApiClient._internal() {
    _dio = Dio(
      BaseOptions(
        baseUrl: AppConfig.apiBaseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
        headers: {'Content-Type': 'application/json'},
      ),
    );
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await TokenStorage.instance.accessToken;
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: (DioException error, handler) async {
          final isUnauthorized = error.response?.statusCode == 401;
          final alreadyRetried = error.requestOptions.extra['retried'] == true;

          if (isUnauthorized && !alreadyRetried) {
            final refreshed = await _tryRefresh();
            if (refreshed) {
              final retryOptions = error.requestOptions;
              retryOptions.extra['retried'] = true;
              final token = await TokenStorage.instance.accessToken;
              retryOptions.headers['Authorization'] = 'Bearer $token';
              try {
                final response = await _dio.fetch(retryOptions);
                handler.resolve(response);
                return;
              } catch (_) {
                // Fall through to the original error below.
              }
            }
          }
          handler.next(error);
        },
      ),
    );
  }

  static final ApiClient instance = ApiClient._internal();

  late final Dio _dio;

  Future<bool> _tryRefresh() async {
    final refreshToken = await TokenStorage.instance.refreshToken;
    if (refreshToken == null) return false;
    try {
      final response = await _dio.post(
        '/auth/refresh/',
        data: {'refresh': refreshToken},
      );
      final newAccess = response.data['access'] as String?;
      if (newAccess == null) return false;
      await TokenStorage.instance.updateAccessToken(newAccess);
      return true;
    } catch (_) {
      await TokenStorage.instance.clear();
      return false;
    }
  }

  /// Unwraps the backend's {"error": {"code", "message"}} envelope into a
  /// clean ApiException, otherwise falls back to a generic one.
  ApiException _asApiException(DioException error) {
    final data = error.response?.data;
    if (data is Map && data['error'] is Map) {
      final errorBody = data['error'] as Map;
      return ApiException(
        errorBody['message']?.toString() ?? 'Something went wrong.',
        code: errorBody['code']?.toString(),
        statusCode: error.response?.statusCode,
      );
    }
    return ApiException(
      error.message ?? 'Network error. Please check your connection.',
      statusCode: error.response?.statusCode,
    );
  }

  Future<Map<String, dynamic>> get(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      final response = await _dio.get(path, queryParameters: queryParameters);
      return response.data as Map<String, dynamic>;
    } on DioException catch (error) {
      throw _asApiException(error);
    }
  }

  /// For the handful of endpoints (e.g. candidate lists) that return a
  /// bare JSON array rather than the usual {"results": [...]} paginated
  /// envelope.
  Future<List<dynamic>> getList(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      final response = await _dio.get(path, queryParameters: queryParameters);
      return response.data as List<dynamic>;
    } on DioException catch (error) {
      throw _asApiException(error);
    }
  }

  Future<Map<String, dynamic>> post(String path, {Object? data}) async {
    try {
      final response = await _dio.post(path, data: data);
      return response.data as Map<String, dynamic>;
    } on DioException catch (error) {
      throw _asApiException(error);
    }
  }

  Future<Map<String, dynamic>> patch(String path, {Object? data}) async {
    try {
      final response = await _dio.patch(path, data: data);
      return response.data as Map<String, dynamic>;
    } on DioException catch (error) {
      throw _asApiException(error);
    }
  }

  Future<void> delete(String path) async {
    try {
      await _dio.delete(path);
    } on DioException catch (error) {
      throw _asApiException(error);
    }
  }
}
