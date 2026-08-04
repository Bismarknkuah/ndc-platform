import 'package:flutter_test/flutter_test.dart';

import 'package:ndc_mobile/features/elections/election_models.dart';
import 'package:ndc_mobile/features/events/events_provider.dart';

void main() {
  group('Candidate.fromJson', () {
    test('parses a full candidate with party and photo', () {
      final candidate = Candidate.fromJson({
        'id': 'abc123',
        'name': 'Jane Doe',
        'position': 'President',
        'party': 'NDC',
        'photo_base64': 'ZmFrZQ==',
      });

      expect(candidate.id, 'abc123');
      expect(candidate.name, 'Jane Doe');
      expect(candidate.position, 'President');
      expect(candidate.party, 'NDC');
      expect(candidate.photoBase64, 'ZmFrZQ==');
    });

    test('handles a candidate with no position/party/photo (single-race poll option)', () {
      final candidate = Candidate.fromJson({'id': 'x', 'name': 'Option A'});

      expect(candidate.position, isNull);
      expect(candidate.party, isNull);
      expect(candidate.photoBase64, isNull);
    });
  });

  group('EligibilityStatus.fromJson', () {
    test('parses eligibility and voted positions', () {
      final status = EligibilityStatus.fromJson({
        'eligible': true,
        'election_status': 'OPEN',
        'voted_positions': ['President'],
      });

      expect(status.eligible, isTrue);
      expect(status.electionStatus, 'OPEN');
      expect(status.hasVotedFor('President'), isTrue);
      expect(status.hasVotedFor('Treasurer'), isFalse);
    });

    test('defaults safely on missing fields', () {
      final status = EligibilityStatus.fromJson(const {});

      expect(status.eligible, isFalse);
      expect(status.electionStatus, '');
      expect(status.votedPositions, isEmpty);
    });
  });

  group('EventSummary.fromJson', () {
    test('parses a full event', () {
      final event = EventSummary.fromJson({
        'id': 'ev1',
        'title': 'National Rally',
        'event_type': 'RALLY',
        'location': 'Independence Square, Accra',
        'status': 'SCHEDULED',
        'scheduled_start': '2026-08-15T10:00:00Z',
      });

      expect(event.title, 'National Rally');
      expect(event.eventType, 'RALLY');
      expect(event.location, 'Independence Square, Accra');
      expect(event.scheduledStart.year, 2026);
    });
  });
}
