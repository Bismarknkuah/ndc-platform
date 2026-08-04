class ElectionSummary {
  ElectionSummary({
    required this.id,
    required this.title,
    required this.electionType,
    required this.status,
    required this.startDate,
    required this.endDate,
  });

  factory ElectionSummary.fromJson(Map<String, dynamic> json) => ElectionSummary(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        electionType: json['election_type'] as String? ?? '',
        status: json['status'] as String? ?? '',
        startDate: DateTime.tryParse(json['start_date'] as String? ?? '') ?? DateTime.now(),
        endDate: DateTime.tryParse(json['end_date'] as String? ?? '') ?? DateTime.now(),
      );

  final String id;
  final String title;
  final String electionType;
  final String status;
  final DateTime startDate;
  final DateTime endDate;
}

class Candidate {
  Candidate({
    required this.id,
    required this.name,
    required this.position,
    required this.party,
    required this.photoBase64,
  });

  factory Candidate.fromJson(Map<String, dynamic> json) => Candidate(
        id: json['id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        position: json['position'] as String?,
        party: json['party'] as String?,
        photoBase64: json['photo_base64'] as String?,
      );

  final String id;
  final String name;
  final String? position;
  final String? party;
  final String? photoBase64;
}

class EligibilityStatus {
  EligibilityStatus({
    required this.eligible,
    required this.electionStatus,
    required this.votedPositions,
  });

  factory EligibilityStatus.fromJson(Map<String, dynamic> json) => EligibilityStatus(
        eligible: json['eligible'] as bool? ?? false,
        electionStatus: json['election_status'] as String? ?? '',
        votedPositions:
            ((json['voted_positions'] as List<dynamic>?) ?? []).map((e) => e as String?).toList(),
      );

  final bool eligible;
  final String electionStatus;
  final List<String?> votedPositions;

  bool hasVotedFor(String? position) => votedPositions.contains(position);
}
