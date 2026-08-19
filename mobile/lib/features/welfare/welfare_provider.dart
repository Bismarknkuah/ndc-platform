import 'package:flutter/foundation.dart';

import '../../core/api_client.dart';

const welfareCategories = ['BEREAVEMENT', 'MEDICAL', 'EDUCATIONAL', 'EMERGENCY', 'OTHER'];

class WelfareRequestSummary {
  WelfareRequestSummary({
    required this.id,
    required this.category,
    required this.description,
    required this.amountRequested,
    required this.status,
    required this.createdAt,
  });

  factory WelfareRequestSummary.fromJson(Map<String, dynamic> json) => WelfareRequestSummary(
        id: json['id'] as String? ?? '',
        category: json['category'] as String? ?? '',
        description: json['description'] as String? ?? '',
        amountRequested: json['amount_requested'] as String? ?? '0',
        status: json['status'] as String? ?? '',
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      );

  final String id;
  final String category;
  final String description;
  final String amountRequested;
  final String status;
  final DateTime createdAt;
}

class WelfareProvider extends ChangeNotifier {
  List<WelfareRequestSummary> myRequests = [];
  bool isLoading = false;
  bool isSubmitting = false;
  String? error;
  String? submitError;

  Future<void> load() async {
    isLoading = true;
    error = null;
    notifyListeners();
    try {
      final response = await ApiClient.instance.get('/welfare/requests/');
      final results = response['results'] as List<dynamic>? ?? [];
      myRequests =
          results.map((e) => WelfareRequestSummary.fromJson(e as Map<String, dynamic>)).toList();
    } on ApiException catch (err) {
      error = err.message;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> submit({
    required String category,
    required String description,
    required String amountRequested,
  }) async {
    isSubmitting = true;
    submitError = null;
    notifyListeners();
    try {
      await ApiClient.instance.post(
        '/welfare/requests/',
        data: {
          'category': category,
          'description': description,
          'amount_requested': amountRequested,
        },
      );
      await load();
      return true;
    } on ApiException catch (err) {
      submitError = err.message;
      return false;
    } finally {
      isSubmitting = false;
      notifyListeners();
    }
  }
}
