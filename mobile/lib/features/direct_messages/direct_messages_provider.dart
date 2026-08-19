import 'package:flutter/foundation.dart';

import '../../core/api_client.dart';

class DirectMessage {
  DirectMessage({
    required this.id,
    required this.senderId,
    required this.senderName,
    required this.recipientId,
    required this.recipientName,
    required this.body,
    required this.readAt,
    required this.createdAt,
  });

  factory DirectMessage.fromJson(Map<String, dynamic> json) => DirectMessage(
        id: json['id'] as String? ?? '',
        senderId: (json['sender'] as Map?)?['id'] as String? ?? '',
        senderName: (json['sender'] as Map?)?['full_name'] as String? ?? '',
        recipientId: (json['recipient'] as Map?)?['id'] as String? ?? '',
        recipientName: (json['recipient'] as Map?)?['full_name'] as String? ?? '',
        body: json['body'] as String? ?? '',
        readAt: json['read_at'] != null ? DateTime.tryParse(json['read_at'] as String) : null,
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      );

  final String id;
  final String senderId;
  final String senderName;
  final String recipientId;
  final String recipientName;
  final String body;
  final DateTime? readAt;
  final DateTime createdAt;
}

/// One row in the inbox: the other party in a conversation, and their
/// most recent message. Derived client-side since the backend exposes a
/// flat message list, not a dedicated conversations endpoint.
class ConversationSummary {
  ConversationSummary({
    required this.otherPartyId,
    required this.otherPartyName,
    required this.lastMessage,
  });

  final String otherPartyId;
  final String otherPartyName;
  final DirectMessage lastMessage;
}

class DirectMessagesInboxProvider extends ChangeNotifier {
  List<ConversationSummary> conversations = [];
  bool isLoading = false;
  String? error;
  String? _currentUserId;

  Future<void> load(String currentUserId) async {
    _currentUserId = currentUserId;
    isLoading = true;
    error = null;
    notifyListeners();
    try {
      final response = await ApiClient.instance.get('/messaging/direct-messages/');
      final results = response['results'] as List<dynamic>? ?? [];
      final messages =
          results.map((e) => DirectMessage.fromJson(e as Map<String, dynamic>)).toList();

      final byPartner = <String, ConversationSummary>{};
      for (final message in messages) {
        final isOutgoing = message.senderId == _currentUserId;
        final partnerId = isOutgoing ? message.recipientId : message.senderId;
        final partnerName = isOutgoing ? message.recipientName : message.senderName;
        final existing = byPartner[partnerId];
        if (existing == null || message.createdAt.isAfter(existing.lastMessage.createdAt)) {
          byPartner[partnerId] = ConversationSummary(
            otherPartyId: partnerId,
            otherPartyName: partnerName,
            lastMessage: message,
          );
        }
      }
      conversations = byPartner.values.toList()
        ..sort((a, b) => b.lastMessage.createdAt.compareTo(a.lastMessage.createdAt));
    } on ApiException catch (err) {
      error = err.message;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }
}

class ConversationProvider extends ChangeNotifier {
  List<DirectMessage> messages = [];
  bool isLoading = false;
  bool isSending = false;
  String? error;

  Future<void> load(String otherUserId) async {
    isLoading = true;
    error = null;
    notifyListeners();
    try {
      final response = await ApiClient.instance.get(
        '/messaging/direct-messages/',
        queryParameters: {'with': otherUserId},
      );
      final results = response['results'] as List<dynamic>? ?? [];
      messages = results.map((e) => DirectMessage.fromJson(e as Map<String, dynamic>)).toList();
    } on ApiException catch (err) {
      error = err.message;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> send(String otherUserId, String body) async {
    isSending = true;
    notifyListeners();
    try {
      await ApiClient.instance.post(
        '/messaging/direct-messages/',
        data: {'recipient_id': otherUserId, 'body': body},
      );
      await load(otherUserId);
      return true;
    } on ApiException {
      return false;
    } finally {
      isSending = false;
      notifyListeners();
    }
  }
}
