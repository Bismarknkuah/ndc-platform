import 'package:flutter/foundation.dart';

import '../../core/api_client.dart';

class GroupMember {
  GroupMember({required this.id, required this.fullName});

  factory GroupMember.fromJson(Map<String, dynamic> json) => GroupMember(
        id: json['id'] as String? ?? '',
        fullName: json['full_name'] as String? ?? '',
      );

  final String id;
  final String fullName;
}

class DiscussionGroup {
  DiscussionGroup({
    required this.id,
    required this.name,
    required this.description,
    required this.members,
  });

  factory DiscussionGroup.fromJson(Map<String, dynamic> json) => DiscussionGroup(
        id: json['id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        description: json['description'] as String? ?? '',
        members: ((json['members'] as List<dynamic>?) ?? [])
            .map((m) => GroupMember.fromJson(m as Map<String, dynamic>))
            .toList(),
      );

  final String id;
  final String name;
  final String description;
  final List<GroupMember> members;
}

class GroupMessage {
  GroupMessage({
    required this.id,
    required this.senderName,
    required this.body,
    required this.createdAt,
  });

  factory GroupMessage.fromJson(Map<String, dynamic> json) => GroupMessage(
        id: json['id'] as String? ?? '',
        senderName: (json['sender'] as Map?)?['full_name'] as String? ?? '',
        body: json['body'] as String? ?? '',
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      );

  final String id;
  final String senderName;
  final String body;
  final DateTime createdAt;
}

class GroupsProvider extends ChangeNotifier {
  List<DiscussionGroup> groups = [];
  bool isLoading = false;
  bool isCreating = false;
  String? error;

  Future<void> load() async {
    isLoading = true;
    error = null;
    notifyListeners();
    try {
      final response = await ApiClient.instance.get('/messaging/groups/');
      final results = response['results'] as List<dynamic>? ?? [];
      groups = results.map((e) => DiscussionGroup.fromJson(e as Map<String, dynamic>)).toList();
    } on ApiException catch (err) {
      error = err.message;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> createGroup(String name, String description) async {
    isCreating = true;
    notifyListeners();
    try {
      await ApiClient.instance.post(
        '/messaging/groups/',
        data: {'name': name, 'description': description},
      );
      await load();
      return true;
    } on ApiException {
      return false;
    } finally {
      isCreating = false;
      notifyListeners();
    }
  }
}

class GroupMessagesProvider extends ChangeNotifier {
  List<GroupMessage> messages = [];
  bool isLoading = false;
  bool isSending = false;
  String? error;

  Future<void> load(String groupId) async {
    isLoading = true;
    error = null;
    notifyListeners();
    try {
      final response = await ApiClient.instance.get('/messaging/groups/$groupId/messages/');
      final results = response['results'] as List<dynamic>? ?? [];
      messages = results.map((e) => GroupMessage.fromJson(e as Map<String, dynamic>)).toList();
    } on ApiException catch (err) {
      error = err.message;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> send(String groupId, String body) async {
    isSending = true;
    notifyListeners();
    try {
      await ApiClient.instance.post('/messaging/groups/$groupId/messages/', data: {'body': body});
      await load(groupId);
      return true;
    } on ApiException {
      return false;
    } finally {
      isSending = false;
      notifyListeners();
    }
  }
}
