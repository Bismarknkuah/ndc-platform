class RoleSummary {
  RoleSummary({required this.name, required this.code, required this.scope});

  factory RoleSummary.fromJson(Map<String, dynamic> json) => RoleSummary(
        name: json['name'] as String? ?? '',
        code: json['code'] as String? ?? '',
        scope: json['scope'] as String? ?? '',
      );

  final String name;
  final String code;
  final String scope;
}

class OrganizationalUnitSummary {
  OrganizationalUnitSummary({
    required this.id,
    required this.name,
    required this.unitType,
  });

  factory OrganizationalUnitSummary.fromJson(Map<String, dynamic> json) =>
      OrganizationalUnitSummary(
        id: json['id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        unitType: json['unit_type'] as String? ?? '',
      );

  final String id;
  final String name;
  final String unitType;
}

class NdcUser {
  NdcUser({
    required this.id,
    required this.email,
    required this.fullName,
    required this.membershipId,
    this.role,
    this.organizationalUnit,
  });

  factory NdcUser.fromJson(Map<String, dynamic> json) => NdcUser(
        id: json['id'] as String? ?? '',
        email: json['email'] as String? ?? '',
        fullName: json['full_name'] as String? ?? '',
        membershipId: json['membership_id'] as String? ?? '',
        role: json['role'] != null
            ? RoleSummary.fromJson(json['role'] as Map<String, dynamic>)
            : null,
        organizationalUnit: json['organizational_unit'] != null
            ? OrganizationalUnitSummary.fromJson(
                json['organizational_unit'] as Map<String, dynamic>,
              )
            : null,
      );

  final String id;
  final String email;
  final String fullName;
  final String membershipId;
  final RoleSummary? role;
  final OrganizationalUnitSummary? organizationalUnit;
}
