import 'user.dart';

class MeetingSummary {
  MeetingSummary({
    required this.id,
    required this.title,
    required this.meetingType,
    required this.scheduledStart,
    required this.meetingUrl,
  });

  factory MeetingSummary.fromJson(Map<String, dynamic> json) =>
      MeetingSummary(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        meetingType: json['meeting_type'] as String? ?? '',
        scheduledStart:
            DateTime.tryParse(json['scheduled_start'] as String? ?? '') ??
                DateTime.now(),
        meetingUrl: json['meeting_url'] as String? ?? '',
      );

  final String id;
  final String title;
  final String meetingType;
  final DateTime scheduledStart;
  final String meetingUrl;
}

class TaskSummary {
  TaskSummary({
    required this.id,
    required this.title,
    required this.engagementType,
    required this.platformName,
    required this.scheduledAt,
    required this.status,
  });

  factory TaskSummary.fromJson(Map<String, dynamic> json) => TaskSummary(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        engagementType: json['engagement_type'] as String? ?? '',
        platformName: json['platform_name'] as String? ?? '',
        scheduledAt: DateTime.tryParse(json['scheduled_at'] as String? ?? '') ??
            DateTime.now(),
        status: json['status'] as String? ?? '',
      );

  final String id;
  final String title;
  final String engagementType;
  final String platformName;
  final DateTime scheduledAt;
  final String status;
}

class TeamLedSummary {
  TeamLedSummary({
    required this.departmentName,
    required this.unitName,
    required this.position,
    required this.teamSize,
    required this.pendingTasks,
  });

  factory TeamLedSummary.fromJson(Map<String, dynamic> json) =>
      TeamLedSummary(
        departmentName: (json['department'] as Map?)?['name'] as String? ?? '',
        unitName:
            (json['organizational_unit'] as Map?)?['name'] as String? ?? '',
        position: json['position'] as String? ?? '',
        teamSize: json['team_size'] as int? ?? 0,
        pendingTasks: json['pending_tasks'] as int? ?? 0,
      );

  final String departmentName;
  final String unitName;
  final String position;
  final int teamSize;
  final int pendingTasks;
}

/// Wraps the raw /api/v1/dashboard/ payload. Sections are optional on the
/// backend (only present if relevant to the caller's role), so every
/// accessor here defaults to an empty/null value rather than throwing.
class DashboardData {
  DashboardData(this._raw);

  final Map<String, dynamic> _raw;

  NdcUser get profile =>
      NdcUser.fromJson(_raw['profile'] as Map<String, dynamic>);

  int get unreadNotificationCount =>
      _raw['unread_notification_count'] as int? ?? 0;

  List<MeetingSummary> get upcomingMeetings =>
      ((_raw['upcoming_meetings'] as List<dynamic>?) ?? [])
          .map(
              (item) => MeetingSummary.fromJson(item as Map<String, dynamic>))
          .toList();

  List<TaskSummary> get pendingTasks =>
      ((_raw['pending_tasks'] as List<dynamic>?) ?? [])
          .map((item) => TaskSummary.fromJson(item as Map<String, dynamic>))
          .toList();

  List<TeamLedSummary>? get teamsLed {
    final raw = _raw['teams_led'] as List<dynamic>?;
    if (raw == null) return null;
    return raw
        .map((item) => TeamLedSummary.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Map<String, dynamic>? get financeSummary =>
      _raw['finance_summary'] as Map<String, dynamic>?;

  List<Map<String, dynamic>>? get activeElections =>
      (_raw['active_elections'] as List<dynamic>?)
          ?.cast<Map<String, dynamic>>();

  List<Map<String, dynamic>>? get upcomingEvents => (_raw['upcoming_events']
          as List<dynamic>?)
      ?.cast<Map<String, dynamic>>();
}
