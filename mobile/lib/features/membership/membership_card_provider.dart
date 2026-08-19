import 'package:flutter/foundation.dart';

import '../../core/api_client.dart';

class MembershipCardData {
  MembershipCardData({
    required this.membershipId,
    required this.fullName,
    required this.role,
    required this.organizationalUnit,
    required this.qrCodeBase64,
  });

  factory MembershipCardData.fromJson(Map<String, dynamic> json) =>
      MembershipCardData(
        membershipId: json['membership_id'] as String? ?? '',
        fullName: json['full_name'] as String? ?? '',
        role: json['role'] as String? ?? '',
        organizationalUnit: json['organizational_unit'] as String? ?? '',
        qrCodeBase64: json['qr_code_base64'] as String? ?? '',
      );

  final String membershipId;
  final String fullName;
  final String role;
  final String organizationalUnit;
  final String qrCodeBase64;
}

class MembershipCardProvider extends ChangeNotifier {
  MembershipCardData? card;
  bool isLoading = false;
  bool isReissuing = false;
  String? error;

  Future<void> load() async {
    isLoading = true;
    error = null;
    notifyListeners();
    try {
      final response = await ApiClient.instance.get('/membership/card/');
      card = MembershipCardData.fromJson(response);
    } on ApiException catch (err) {
      error = err.message;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<void> reissue() async {
    isReissuing = true;
    notifyListeners();
    try {
      final response = await ApiClient.instance.post('/membership/card/reissue/');
      card = MembershipCardData.fromJson(response);
    } on ApiException catch (err) {
      error = err.message;
    } finally {
      isReissuing = false;
      notifyListeners();
    }
  }
}
