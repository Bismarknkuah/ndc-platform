class NdcNotification {
  NdcNotification({
    required this.id,
    required this.notificationType,
    required this.title,
    required this.body,
    required this.isRead,
    required this.createdAt,
  });

  factory NdcNotification.fromJson(Map<String, dynamic> json) =>
      NdcNotification(
        id: json['id'] as String? ?? '',
        notificationType: json['notification_type'] as String? ?? '',
        title: json['title'] as String? ?? '',
        body: json['body'] as String? ?? '',
        isRead: json['is_read'] as bool? ?? false,
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ??
            DateTime.now(),
      );

  final String id;
  final String notificationType;
  final String title;
  final String body;
  final bool isRead;
  final DateTime createdAt;
}
