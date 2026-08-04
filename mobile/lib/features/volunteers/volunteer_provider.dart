import 'package:flutter/foundation.dart';

import '../../core/api_client.dart';

class VolunteerOpportunity {
  VolunteerOpportunity({
    required this.id,
    required this.title,
    required this.description,
    required this.location,
    required this.neededCount,
    required this.filledCount,
    required this.status,
    required this.scheduledStart,
  });

  factory VolunteerOpportunity.fromJson(Map<String, dynamic> json) => VolunteerOpportunity(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        description: json['description'] as String? ?? '',
        location: json['location'] as String? ?? '',
        neededCount: json['needed_count'] as int? ?? 0,
        filledCount: json['filled_count'] as int? ?? 0,
        status: json['status'] as String? ?? '',
        scheduledStart:
            DateTime.tryParse(json['scheduled_start'] as String? ?? '') ?? DateTime.now(),
      );

  final String id;
  final String title;
  final String description;
  final String location;
  final int neededCount;
  final int filledCount;
  final String status;
  final DateTime scheduledStart;

  bool get isFull => filledCount >= neededCount;
}

class VolunteerProvider extends ChangeNotifier {
  List<VolunteerOpportunity> opportunities = [];
  bool isLoading = false;
  String? error;
  final Set<String> _signedUp = {};
  final Set<String> _signupInFlight = {};

  bool isSignedUp(String opportunityId) => _signedUp.contains(opportunityId);

  bool isSigningUp(String opportunityId) => _signupInFlight.contains(opportunityId);

  Future<void> load() async {
    isLoading = true;
    error = null;
    notifyListeners();
    try {
      final response = await ApiClient.instance.get(
        '/volunteers/opportunities/',
        queryParameters: {'upcoming': 'true'},
      );
      final results = response['results'] as List<dynamic>? ?? [];
      opportunities =
          results.map((e) => VolunteerOpportunity.fromJson(e as Map<String, dynamic>)).toList();
    } on ApiException catch (err) {
      error = err.message;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> signUp(String opportunityId) async {
    _signupInFlight.add(opportunityId);
    notifyListeners();
    try {
      await ApiClient.instance.post('/volunteers/opportunities/$opportunityId/signup/');
      _signedUp.add(opportunityId);
      await load();
      return true;
    } on ApiException {
      return false;
    } finally {
      _signupInFlight.remove(opportunityId);
      notifyListeners();
    }
  }
}
