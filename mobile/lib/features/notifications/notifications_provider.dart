import 'package:flutter/foundation.dart';

import '../../core/api_client.dart';
import '../../models/notification.dart';

class NotificationsProvider extends ChangeNotifier {
  List<NdcNotification> notifications = [];
  bool isLoading = false;
  String? error;

  Future<void> load() async {
    isLoading = true;
    error = null;
    notifyListeners();

    try {
      final response = await ApiClient.instance.get('/messaging/notifications/');
      final results = response['results'] as List<dynamic>? ?? [];
      notifications = results
          .map((item) => NdcNotification.fromJson(item as Map<String, dynamic>))
          .toList();
    } on ApiException catch (err) {
      error = err.message;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<void> markRead(String notificationId) async {
    try {
      await ApiClient.instance.post('/messaging/notifications/$notificationId/read/');
      final index = notifications.indexWhere((n) => n.id == notificationId);
      if (index != -1) {
        final old = notifications[index];
        notifications[index] = NdcNotification(
          id: old.id,
          notificationType: old.notificationType,
          title: old.title,
          body: old.body,
          isRead: true,
          createdAt: old.createdAt,
        );
        notifyListeners();
      }
    } on ApiException {
      // Non-fatal: the list will simply show it as unread until next refresh.
    }
  }

  Future<void> markAllRead() async {
    try {
      await ApiClient.instance.post('/messaging/notifications/mark-all-read/');
      await load();
    } on ApiException {
      // Non-fatal.
    }
  }
}
