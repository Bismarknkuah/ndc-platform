import 'package:flutter/foundation.dart';

import '../../core/api_client.dart';
import 'election_models.dart';

class ElectionsProvider extends ChangeNotifier {
  List<ElectionSummary> elections = [];
  bool isLoading = false;
  String? error;

  Future<void> loadElections() async {
    isLoading = true;
    error = null;
    notifyListeners();
    try {
      final response = await ApiClient.instance.get('/elections/');
      final results = response['results'] as List<dynamic>? ?? [];
      elections = results.map((e) => ElectionSummary.fromJson(e as Map<String, dynamic>)).toList();
    } on ApiException catch (err) {
      error = err.message;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }
}

class ElectionDetailProvider extends ChangeNotifier {
  List<Candidate> candidates = [];
  EligibilityStatus? eligibility;
  bool isLoading = false;
  bool isVoting = false;
  String? error;
  String? lastVoteError;

  Future<void> load(String electionId) async {
    isLoading = true;
    error = null;
    notifyListeners();
    try {
      final rawCandidates = await ApiClient.instance.getList('/elections/$electionId/candidates/');
      candidates = rawCandidates.map((c) => Candidate.fromJson(c as Map<String, dynamic>)).toList();

      final eligibilityResponse = await ApiClient.instance.get('/elections/$electionId/my-eligibility/');
      eligibility = EligibilityStatus.fromJson(eligibilityResponse);
    } on ApiException catch (err) {
      error = err.message;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> castVote(String electionId, String candidateId, String? position) async {
    isVoting = true;
    lastVoteError = null;
    notifyListeners();
    try {
      await ApiClient.instance.post(
        '/elections/$electionId/vote/',
        data: {'candidate_id': candidateId, if (position != null) 'position': position},
      );
      await load(electionId);
      return true;
    } on ApiException catch (err) {
      lastVoteError = err.message;
      return false;
    } finally {
      isVoting = false;
      notifyListeners();
    }
  }
}
