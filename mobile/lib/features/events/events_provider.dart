import 'package:flutter/foundation.dart';

import '../../core/api_client.dart';

class EventSummary {
  EventSummary({
    required this.id,
    required this.title,
    required this.eventType,
    required this.location,
    required this.status,
    required this.scheduledStart,
  });

  factory EventSummary.fromJson(Map<String, dynamic> json) => EventSummary(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        eventType: json['event_type'] as String? ?? '',
        location: json['location'] as String? ?? '',
        status: json['status'] as String? ?? '',
        scheduledStart:
            DateTime.tryParse(json['scheduled_start'] as String? ?? '') ?? DateTime.now(),
      );

  final String id;
  final String title;
  final String eventType;
  final String location;
  final String status;
  final DateTime scheduledStart;
}

class EventsProvider extends ChangeNotifier {
  List<EventSummary> events = [];
  bool isLoading = false;
  String? error;
  final Set<String> _rsvpInFlight = {};
  final Map<String, String> _rsvpStatus = {};

  bool isRsvpInFlight(String eventId) => _rsvpInFlight.contains(eventId);

  String? rsvpStatusFor(String eventId) => _rsvpStatus[eventId];

  Future<void> load() async {
    isLoading = true;
    error = null;
    notifyListeners();
    try {
      final response = await ApiClient.instance.get('/events/', queryParameters: {'upcoming': 'true'});
      final results = response['results'] as List<dynamic>? ?? [];
      events = results.map((e) => EventSummary.fromJson(e as Map<String, dynamic>)).toList();
    } on ApiException catch (err) {
      error = err.message;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<void> rsvp(String eventId, String status) async {
    _rsvpInFlight.add(eventId);
    notifyListeners();
    try {
      await ApiClient.instance.post('/events/$eventId/rsvp/', data: {'status': status});
      _rsvpStatus[eventId] = status;
    } on ApiException {
      // Swallow - UI can retry; not fatal to the list view.
    } finally {
      _rsvpInFlight.remove(eventId);
      notifyListeners();
    }
  }
}
