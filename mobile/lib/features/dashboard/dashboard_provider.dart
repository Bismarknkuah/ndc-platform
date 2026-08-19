import 'package:flutter/foundation.dart';

import '../../core/api_client.dart';
import '../../models/dashboard.dart';

class DashboardProvider extends ChangeNotifier {
  DashboardData? data;
  bool isLoading = false;
  String? error;

  Future<void> load() async {
    isLoading = true;
    error = null;
    notifyListeners();

    try {
      final response = await ApiClient.instance.get('/dashboard/');
      data = DashboardData(response);
    } on ApiException catch (err) {
      error = err.message;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }
}
