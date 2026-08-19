import os

from django.core.management.base import BaseCommand

from apps.accounts.documents import Role, User
from apps.departments.documents import Department
from apps.hierarchy.documents import OrganizationalUnit

# A representative, extensible starter set of executive roles across the
# main chain plus every auxiliary structure named in the party's
# constitution. Additional positions can be added via the Role API/admin
# without a code change.
BASE_ROLES = [
    # A distinct role for the true system-administrator identity (attached
    # `is_superadmin=True` bypasses every permission check regardless of
    # this list - kept broad anyway so the account is self-descriptive if
    # is_superadmin is ever unset, and so its Role display name in the UI
    # doesn't look identical to the National Chairman demo account).
    {
        "code": "system_administrator",
        "name": "System Administrator",
        "scope": "NATIONAL",
        "permissions": [
            "hierarchy.manage",
            "hierarchy.manage_roles",
            "finance.manage",
            "finance.view",
            "elections.manage",
            "membership.register",
            "messaging.broadcast.downward",
            "messaging.report.upward",
            "meetings.call",
            "meetings.call_all_members",
            "audit.view",
        ],
    },
    # Main chain - National
    {
        "code": "national_chairman",
        "name": "National Chairman",
        "scope": "NATIONAL",
        "permissions": [
            "hierarchy.manage",
            "hierarchy.manage_roles",
            "finance.manage",
            "finance.view",
            "elections.manage",
            "membership.register",
            "messaging.broadcast.downward",
            "messaging.report.upward",
            "meetings.call",
            "hierarchy.manage_roles",
            "messaging.broadcast.downward",
            "meetings.call_all_members",
            "audit.view",
            "analytics.ground_intelligence",
        ],
    },
    {
        # The Flagbearer is the party's presidential candidate, a
        # distinct constitutional role from National Chairman (the
        # Chairman runs day-to-day party administration; the Flagbearer
        # is the person the party puts forward for the presidency,
        # chosen separately through internal primaries). Both get full
        # national oversight and ground-intelligence access, since both
        # genuinely need visibility across the whole party, not because
        # they are the same office.
        "code": "flagbearer",
        "name": "Flagbearer",
        "scope": "NATIONAL",
        "permissions": [
            "hierarchy.manage",
            "finance.view",
            "elections.manage",
            "messaging.broadcast.downward",
            "messaging.report.upward",
            "meetings.call",
            "meetings.call_all_members",
            "audit.view",
            "analytics.ground_intelligence",
        ],
    },
    {
        "code": "national_general_secretary",
        "name": "National General Secretary",
        "scope": "NATIONAL",
        "permissions": [
            "hierarchy.manage",
            "messaging.broadcast.downward",
            "meetings.call_all_members",
            "audit.view",
            "analytics.ground_intelligence",
        ],
    },
    {
        "code": "national_organizer",
        "name": "National Organizer",
        "scope": "NATIONAL",
        "permissions": ["hierarchy.manage", "messaging.broadcast.downward"],
    },
    {
        # A functional department head's tools should be scoped to their
        # own department's work, not the broader hierarchy-wide
        # oversight a real National Organizer (Article 22 NEC position,
        # above) genuinely carries. This role exists specifically for
        # apps.departments.documents.DepartmentAssignment HEAD/DEPUTY_HEAD
        # positions - do not add hierarchy.manage here.
        "code": "communications_director",
        "name": "Communications Director",
        "scope": "NATIONAL",
        "permissions": ["messaging.broadcast.downward"],
    },
    {
        "code": "membership_officer",
        "name": "Membership Officer",
        "scope": "NATIONAL",
        "permissions": ["membership.register"],
    },
    {
        "code": "national_treasurer",
        "name": "National Treasurer",
        "scope": "NATIONAL",
        "permissions": ["finance.manage", "finance.view"],
    },
    # Article 22(9)(m): appointed (not elected) national officers, and the
    # Internal Auditor named as a standing Finance Committee member
    # (Article 37(1)(e)) - all confirmed from the full constitution read.
    {
        "code": "director_international_relations",
        "name": "Director of International Relations",
        "scope": "NATIONAL",
        "permissions": ["messaging.report.upward"],
    },
    {
        "code": "director_research",
        "name": "Director of Research",
        "scope": "NATIONAL",
        "permissions": ["messaging.report.upward"],
    },
    {
        "code": "director_administration",
        "name": "Director of Administration",
        "scope": "NATIONAL",
        "permissions": ["hierarchy.manage", "messaging.report.upward"],
    },
    {
        "code": "director_elections",
        "name": "Director of Elections",
        "scope": "NATIONAL",
        "permissions": ["elections.manage", "messaging.report.upward"],
    },
    {
        "code": "internal_auditor",
        "name": "Internal Auditor",
        "scope": "NATIONAL",
        "permissions": ["finance.view", "audit.view"],
    },
    {
        "code": "national_women_organizer",
        "name": "National Women's Organizer",
        "scope": "WOMENS_WING",
        "permissions": ["hierarchy.manage", "messaging.broadcast.downward"],
    },
    {
        # Same reasoning as communications_director above: the Women's
        # Affairs *department* head's tools are scoped to that
        # department, distinct from the National Women's Organizer NEC
        # position, which genuinely carries broader authority.
        "code": "womens_affairs_head",
        "name": "Women's Affairs Head",
        "scope": "NATIONAL",
        "permissions": ["messaging.broadcast.downward"],
    },
    {
        "code": "national_youth_organizer",
        "name": "National Youth Organizer",
        "scope": "YOUTH_WING",
        "permissions": ["hierarchy.manage", "messaging.broadcast.downward"],
    },
    # Main chain - Regional
    {
        "code": "regional_chairman",
        "name": "Regional Chairman",
        "scope": "REGIONAL",
        "permissions": [
            "hierarchy.manage",
            "finance.manage",
            "finance.view",
            "elections.manage",
            "membership.register",
            "messaging.broadcast.downward",
            "messaging.report.upward",
            "meetings.call",
        ],
    },
    {
        "code": "regional_secretary",
        "name": "Regional Secretary",
        "scope": "REGIONAL",
        "permissions": ["hierarchy.manage", "messaging.report.upward"],
    },
    # Main chain - Constituency
    {
        "code": "constituency_chairman",
        "name": "Constituency Chairman",
        "scope": "CONSTITUENCY",
        "permissions": [
            "hierarchy.manage",
            "finance.manage",
            "finance.view",
            "elections.manage",
            "membership.register",
            "messaging.broadcast.downward",
            "messaging.report.upward",
            "meetings.call",
        ],
    },
    {
        "code": "constituency_secretary",
        "name": "Constituency Secretary",
        "scope": "CONSTITUENCY",
        "permissions": ["messaging.report.upward", "meetings.call"],
    },
    # Main chain - Branch (Article 11: only National/Regional/Constituency/Branch
    # are official "levels of organisation" - see apps/hierarchy/constants.py)
    {
        "code": "district_coordinator",
        "name": "District Co-ordinator",
        "scope": "DISTRICT_COORDINATING_COMMITTEE",
        # Explicit product decision, by request: full jurisdiction control
        # matching the other four levels, not the coordination-only subset
        # a strict reading of Article 17 would suggest (Article 17 models
        # the District Co-ordinating Committee as coordinating
        # constituencies within a region rather than commanding them, with
        # no elected executive or independent authority of its own - see
        # apps/hierarchy/constants.py for the full citation). Noted here
        # rather than silently changed without a record of the tradeoff.
        "permissions": [
            "hierarchy.manage",
            "finance.manage",
            "finance.view",
            "elections.manage",
            "membership.register",
            "messaging.broadcast.downward",
            "messaging.report.upward",
            "meetings.call",
        ],
    },
    {
        "code": "branch_chairman",
        "name": "Branch Chairman",
        "scope": "BRANCH",
        "permissions": ["messaging.report.upward", "membership.register"],
    },
    {
        "code": "branch_secretary",
        "name": "Branch Secretary",
        "scope": "BRANCH",
        "permissions": [
            "messaging.report.upward",
            "messaging.broadcast.downward",
            "membership.register",
            "finance.view",
            "meetings.call",
        ],
    },
    {
        "code": "ordinary_member",
        "name": "Ordinary Member",
        "scope": "BRANCH",
        "is_executive": False,
        "permissions": ["profile.manage_own"],
    },
    # TEIN
    {
        "code": "tein_national_coordinator",
        "name": "TEIN National Coordinator",
        "scope": "TEIN_NATIONAL",
        "permissions": ["hierarchy.manage", "messaging.broadcast.downward"],
    },
    {
        "code": "tein_campus_coordinator",
        "name": "TEIN Campus Coordinator",
        "scope": "TEIN_CAMPUS",
        "permissions": ["messaging.report.upward"],
    },
    # Auxiliary bodies
    {
        "code": "zongo_caucus_coordinator",
        "name": "Zongo Caucus Coordinator",
        "scope": "ZONGO_CAUCUS",
        "permissions": ["messaging.report.upward"],
    },
    {
        "code": "professionals_forum_convener",
        "name": "Professionals Forum Convener",
        "scope": "PROFESSIONALS_FORUM",
        "permissions": ["messaging.report.upward"],
    },
    {
        "code": "external_branch_chairman",
        "name": "External Branch Chairman",
        "scope": "EXTERNAL_BRANCH",
        "permissions": ["messaging.report.upward"],
    },
    {
        "code": "council_of_elders_chair",
        "name": "Council of Elders Chair",
        "scope": "COUNCIL_OF_ELDERS",
        "permissions": ["messaging.report.upward", "audit.view"],
    },
    {
        "code": "parliamentary_group_leader",
        "name": "Leader of the Party in Parliament",
        "scope": "PARLIAMENTARY_GROUP",
        "permissions": ["messaging.broadcast.downward", "messaging.report.upward"],
    },
    {
        "code": "functional_committee_chair",
        "name": "Functional Committee Chair",
        "scope": "FUNCTIONAL_COMMITTEE",
        "permissions": ["messaging.report.upward"],
    },
    {
        "code": "election_it_director",
        "name": "Election and IT Director",
        "scope": "NATIONAL",
        "permissions": [
            "elections.manage",
            "messaging.broadcast.downward",
            "audit.view",
        ],
    },
]


DEFAULT_DEPARTMENTS = [
    {
        "code": "communications",
        "name": "Communications",
        "description": "Media relations, press, broadcast appearances.",
    },
    {
        "code": "finance",
        "name": "Finance",
        "description": "Party finances, fundraising, and treasury operations.",
    },
    {
        "code": "organizing",
        "name": "Organizing",
        "description": "Grassroots mobilization and organizational structure.",
    },
    {
        "code": "legal-affairs",
        "name": "Legal Affairs",
        "description": "Legal counsel, compliance, and electoral law.",
    },
    {
        "code": "womens-affairs",
        "name": "Women's Affairs",
        "description": "Women's Wing programs and advocacy.",
    },
    {
        "code": "youth-affairs",
        "name": "Youth Affairs",
        "description": "Youth Wing programs and TEIN coordination.",
    },
    {
        "code": "elections",
        "name": "Elections",
        "description": "Election-day operations, polling agents, results collation.",
    },
    {
        "code": "membership",
        "name": "Membership",
        "description": "Recruitment, registration, and membership records.",
    },
    {
        "code": "research-innovation",
        "name": "Research & Innovation",
        "description": "Policy research and data-driven strategy.",
    },
    {
        "code": "it",
        "name": "Information Technology",
        "description": "Platform operations and digital infrastructure.",
    },
    # The remaining four map directly to Article 32's National Committees
    # list (Finance/Legal/Communication/Research are already covered above
    # under their operational names - "legal-affairs", "communications",
    # "research-innovation" - these four had no equivalent yet).
    {
        "code": "political",
        "name": "Political Committee",
        "description": "Political strategy and inter-party relations (Article 32).",
    },
    {
        "code": "economic",
        "name": "Economic Committee",
        "description": "Economic policy formulation (Article 32).",
    },
    {
        "code": "social",
        "name": "Social Committee",
        "description": "Social policy and welfare programs (Article 32).",
    },
    {
        "code": "conflict-resolution",
        "name": "Conflict Resolution Committee",
        "description": "Internal Party conflict mediation (Article 32) - "
        "distinct from the formal Disciplinary Committee (Articles 46-47).",
    },
]


class Command(BaseCommand):
    help = "Seeds base roles, the National organizational unit, and a bootstrap superadmin account."

    def handle(self, *args, **options):
        created_roles = 0
        updated_roles = 0
        for role_def in BASE_ROLES:
            existing = Role.objects(code=role_def["code"]).first()
            if existing is None:
                Role.objects.create(
                    code=role_def["code"],
                    name=role_def["name"],
                    scope=role_def["scope"],
                    is_executive=role_def.get("is_executive", True),
                    permissions=role_def["permissions"],
                )
                created_roles += 1
            else:
                # A role's permission list is code, not user data - it
                # must always match BASE_ROLES exactly, every run, or a
                # permission change (like adding
                # analytics.ground_intelligence to an existing role)
                # silently never takes effect on an environment where
                # that role was already seeded once before. This was a
                # real bug: roles were only ever created once and never
                # brought back in sync afterward.
                existing.name = role_def["name"]
                existing.scope = role_def["scope"]
                existing.is_executive = role_def.get("is_executive", True)
                existing.permissions = role_def["permissions"]
                existing.save()
                updated_roles += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Roles seeded ({created_roles} newly created, {updated_roles} "
                f"updated to match the current code, {len(BASE_ROLES)} total)."
            )
        )

        national_unit = OrganizationalUnit.objects(code="ndc-national").first()
        if national_unit is None:
            national_unit = OrganizationalUnit.objects.create(
                code="ndc-national",
                name="National Democratic Congress - National",
                unit_type="NATIONAL",
            )
            created = True
        else:
            created = False
        self.stdout.write(
            self.style.SUCCESS(
                f"National unit {'created' if created else 'already present'}: {national_unit.name}"
            )
        )

        created_departments = 0
        for dept_def in DEFAULT_DEPARTMENTS:
            if Department.objects(code=dept_def["code"]).first() is None:
                Department.objects.create(**dept_def)
                created_departments += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Departments seeded ({created_departments} newly created, {len(DEFAULT_DEPARTMENTS)} total)."
            )
        )

        admin_email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@ndc.example")
        admin_password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "ChangeMe123!")
        chairman_role = Role.objects.get(code="national_chairman")

        if User.objects(email=admin_email).first():
            self.stdout.write(
                self.style.WARNING(
                    f"Superadmin {admin_email} already exists, skipping."
                )
            )
        else:
            admin = User(
                email=admin_email,
                phone_number="0000000000",
                first_name="System",
                last_name="Administrator",
                membership_id="NDC-SYS-000001",
                organizational_unit=national_unit,
                role=chairman_role,
                is_superadmin=True,
            )
            admin.set_password(admin_password)
            admin.save()
            self.stdout.write(
                self.style.SUCCESS(f"Bootstrap superadmin created: {admin_email}")
            )

        self._seed_demo_accounts(national_unit)
        self._seed_ground_intelligence_sample_data()

    def _seed_demo_accounts(self, national_unit):
        """
        One-click "try it as..." demo accounts, shown as buttons directly
        on the public login page. Deliberately visible to anyone who
        visits the site - a product decision made with the risk
        understood, not an oversight.

        One of these seven, `demo.superadmin@ndc.example`, is a genuine
        `is_superadmin=True` account by explicit request - meaning it
        bypasses every permission check in the entire platform, not just
        this account's own Role's permission list. This is a materially
        larger exposure than the other six (which are real, but each
        still bounded by an actual Role's actual permission list and
        organizational-unit scope) - if this ever needs to be walked
        back, either delete the `is_superadmin: True` demo definition
        below and re-run this command, or simply remove the
        corresponding button in
        frontend/src/components/auth/demo-login-buttons.tsx and
        redeploy the frontend (the account can sit dormant in the
        database with no practical effect if nobody has its
        credentials).

        Changing DEMO_ACCOUNTS_PASSWORD and re-running this command
        refreshes every existing demo account's password (and
        is_superadmin/role, kept in sync with the definitions below)
        rather than skipping them - safe to re-run any time.
        """
        demo_password = os.getenv("DEMO_ACCOUNTS_PASSWORD", "DemoPass123!")

        regional_unit = OrganizationalUnit.objects(code="ndc-demo-regional").first()
        if regional_unit is None:
            regional_unit = OrganizationalUnit.objects.create(
                code="ndc-demo-regional",
                name="Demo Region",
                unit_type="REGIONAL",
                parent=national_unit,
            )

        constituency_unit = OrganizationalUnit.objects(
            code="ndc-demo-constituency"
        ).first()
        if constituency_unit is None:
            constituency_unit = OrganizationalUnit.objects.create(
                code="ndc-demo-constituency",
                name="Demo Constituency",
                unit_type="CONSTITUENCY",
                parent=regional_unit,
            )

        district_unit = OrganizationalUnit.objects(code="ndc-demo-district").first()
        if district_unit is None:
            district_unit = OrganizationalUnit.objects.create(
                code="ndc-demo-district",
                name="Demo District Co-ordinating Committee",
                unit_type="DISTRICT_COORDINATING_COMMITTEE",
                parent=regional_unit,
            )

        branch_unit = OrganizationalUnit.objects(code="ndc-demo-branch").first()
        if branch_unit is None:
            branch_unit = OrganizationalUnit.objects.create(
                code="ndc-demo-branch",
                name="Demo Branch",
                unit_type="BRANCH",
                parent=constituency_unit,
            )

        # Auxiliary structures that sit alongside the main geographic
        # chain rather than within it (Article 17/58-ish territory) -
        # each demo officer below needs a real unit of the matching
        # type to belong to, not just a Role.
        auxiliary_units = {}
        for code, name, unit_type in [
            ("ndc-demo-tein-national", "TEIN National", "TEIN_NATIONAL"),
            ("ndc-demo-tein-campus", "TEIN Demo Campus", "TEIN_CAMPUS"),
            ("ndc-demo-zongo-caucus", "Zongo Caucus", "ZONGO_CAUCUS"),
            (
                "ndc-demo-professionals-forum",
                "Professionals Forum",
                "PROFESSIONALS_FORUM",
            ),
            (
                "ndc-demo-external-branch",
                "Demo External Branch (Diaspora)",
                "EXTERNAL_BRANCH",
            ),
            ("ndc-demo-council-of-elders", "Council of Elders", "COUNCIL_OF_ELDERS"),
            (
                "ndc-demo-parliamentary-group",
                "Parliamentary Group",
                "PARLIAMENTARY_GROUP",
            ),
            (
                "ndc-demo-functional-committee",
                "Demo Functional Committee",
                "FUNCTIONAL_COMMITTEE",
            ),
            ("ndc-demo-womens-wing", "National Women's Wing", "WOMENS_WING"),
            ("ndc-demo-youth-wing", "National Youth Wing", "YOUTH_WING"),
        ]:
            unit = OrganizationalUnit.objects(code=code).first()
            if unit is None:
                unit = OrganizationalUnit.objects.create(
                    code=code, name=name, unit_type=unit_type, parent=national_unit
                )
            auxiliary_units[unit_type] = unit

        demo_definitions = [
            {
                "email": "demo.superadmin@ndc.example",
                "membership_id": "NDC-DEMO-000000",
                "first_name": "Demo",
                "last_name": "Superadmin",
                "role_code": "system_administrator",
                "unit": national_unit,
                "is_superadmin": True,
            },
            {
                "email": "demo.national@ndc.example",
                "membership_id": "NDC-DEMO-000001",
                "first_name": "Demo",
                "last_name": "National Chairman",
                "role_code": "national_chairman",
                "unit": national_unit,
            },
            {
                "email": "demo.flagbearer@ndc.example",
                "membership_id": "NDC-DEMO-000012",
                "first_name": "Demo",
                "last_name": "Flagbearer",
                "role_code": "flagbearer",
                "unit": national_unit,
            },
            {
                "email": "demo.regional@ndc.example",
                "membership_id": "NDC-DEMO-000002",
                "first_name": "Demo",
                "last_name": "Regional Chairman",
                "role_code": "regional_chairman",
                "unit": regional_unit,
            },
            {
                "email": "demo.district@ndc.example",
                "membership_id": "NDC-DEMO-000006",
                "first_name": "Demo",
                "last_name": "District Co-ordinator",
                "role_code": "district_coordinator",
                "unit": district_unit,
            },
            {
                "email": "demo.constituency@ndc.example",
                "membership_id": "NDC-DEMO-000003",
                "first_name": "Demo",
                "last_name": "Constituency Chairman",
                "role_code": "constituency_chairman",
                "unit": constituency_unit,
            },
            {
                "email": "demo.branch@ndc.example",
                "membership_id": "NDC-DEMO-000004",
                "first_name": "Demo",
                "last_name": "Branch Secretary",
                "role_code": "branch_secretary",
                "unit": branch_unit,
            },
            {
                "email": "demo.member@ndc.example",
                "membership_id": "NDC-DEMO-000005",
                "first_name": "Demo",
                "last_name": "Ordinary Member",
                "role_code": "ordinary_member",
                "unit": branch_unit,
            },
            # Department-head demo accounts, added so the dashboard's
            # department-based differentiation (a Communications
            # Director's dashboard looks different from a Treasurer's)
            # has real accounts to actually demonstrate it with - each
            # gets a real DepartmentAssignment(position="HEAD") below,
            # not just a Role.
            {
                "email": "demo.comms@ndc.example",
                "membership_id": "NDC-DEMO-000007",
                "first_name": "Demo",
                "last_name": "Communications Director",
                "role_code": "communications_director",
                "unit": national_unit,
                "department_code": "communications",
            },
            {
                "email": "demo.treasurer@ndc.example",
                "membership_id": "NDC-DEMO-000008",
                "first_name": "Demo",
                "last_name": "National Treasurer",
                "role_code": "national_treasurer",
                "unit": national_unit,
                "department_code": "finance",
            },
            {
                "email": "demo.elections@ndc.example",
                "membership_id": "NDC-DEMO-000009",
                "first_name": "Demo",
                "last_name": "Elections Director",
                "role_code": "director_elections",
                "unit": national_unit,
                "department_code": "elections",
            },
            {
                "email": "demo.membership@ndc.example",
                "membership_id": "NDC-DEMO-000010",
                "first_name": "Demo",
                "last_name": "Membership Officer",
                "role_code": "membership_officer",
                "unit": national_unit,
                "department_code": "membership",
            },
            {
                "email": "demo.women@ndc.example",
                "membership_id": "NDC-DEMO-000011",
                "first_name": "Demo",
                "last_name": "Women's Affairs Director",
                "role_code": "womens_affairs_head",
                "unit": national_unit,
                "department_code": "womens-affairs",
            },
            # National Secretariat officers (Article 22-ish appointed
            # positions) not otherwise covered above.
            {
                "email": "demo.secretary@ndc.example",
                "membership_id": "NDC-DEMO-000013",
                "first_name": "Demo",
                "last_name": "General Secretary",
                "role_code": "national_general_secretary",
                "unit": national_unit,
            },
            {
                "email": "demo.organizer@ndc.example",
                "membership_id": "NDC-DEMO-000014",
                "first_name": "Demo",
                "last_name": "National Organizer",
                "role_code": "national_organizer",
                "unit": national_unit,
            },
            {
                "email": "demo.intrelations@ndc.example",
                "membership_id": "NDC-DEMO-000015",
                "first_name": "Demo",
                "last_name": "Director, International Relations",
                "role_code": "director_international_relations",
                "unit": national_unit,
            },
            {
                "email": "demo.research@ndc.example",
                "membership_id": "NDC-DEMO-000016",
                "first_name": "Demo",
                "last_name": "Director, Research",
                "role_code": "director_research",
                "unit": national_unit,
            },
            {
                "email": "demo.administration@ndc.example",
                "membership_id": "NDC-DEMO-000017",
                "first_name": "Demo",
                "last_name": "Director, Administration",
                "role_code": "director_administration",
                "unit": national_unit,
            },
            {
                "email": "demo.auditor@ndc.example",
                "membership_id": "NDC-DEMO-000018",
                "first_name": "Demo",
                "last_name": "Internal Auditor",
                "role_code": "internal_auditor",
                "unit": national_unit,
            },
            {
                "email": "demo.womenswing@ndc.example",
                "membership_id": "NDC-DEMO-000019",
                "first_name": "Demo",
                "last_name": "National Women's Organizer",
                "role_code": "national_women_organizer",
                "unit": auxiliary_units["WOMENS_WING"],
            },
            {
                "email": "demo.youthwing@ndc.example",
                "membership_id": "NDC-DEMO-000020",
                "first_name": "Demo",
                "last_name": "National Youth Organizer",
                "role_code": "national_youth_organizer",
                "unit": auxiliary_units["YOUTH_WING"],
            },
            {
                "email": "demo.itdirector@ndc.example",
                "membership_id": "NDC-DEMO-000021",
                "first_name": "Demo",
                "last_name": "Election IT Director",
                "role_code": "election_it_director",
                "unit": national_unit,
                "department_code": "it",
            },
            # Regional/Constituency/Branch officers not otherwise
            # covered by the hierarchy-chairman demo accounts above.
            {
                "email": "demo.regionalsec@ndc.example",
                "membership_id": "NDC-DEMO-000022",
                "first_name": "Demo",
                "last_name": "Regional Secretary",
                "role_code": "regional_secretary",
                "unit": regional_unit,
            },
            {
                "email": "demo.constituencysec@ndc.example",
                "membership_id": "NDC-DEMO-000023",
                "first_name": "Demo",
                "last_name": "Constituency Secretary",
                "role_code": "constituency_secretary",
                "unit": constituency_unit,
            },
            {
                "email": "demo.branchchairman@ndc.example",
                "membership_id": "NDC-DEMO-000024",
                "first_name": "Demo",
                "last_name": "Branch Chairman",
                "role_code": "branch_chairman",
                "unit": branch_unit,
            },
            # Auxiliary structure leaders - TEIN, Zongo Caucus,
            # Professionals Forum, External Branches, Council of
            # Elders, the Parliamentary Group, and a Functional
            # (Article 32) Committee.
            {
                "email": "demo.tein@ndc.example",
                "membership_id": "NDC-DEMO-000025",
                "first_name": "Demo",
                "last_name": "TEIN National Coordinator",
                "role_code": "tein_national_coordinator",
                "unit": auxiliary_units["TEIN_NATIONAL"],
            },
            {
                "email": "demo.teincampus@ndc.example",
                "membership_id": "NDC-DEMO-000026",
                "first_name": "Demo",
                "last_name": "TEIN Campus Coordinator",
                "role_code": "tein_campus_coordinator",
                "unit": auxiliary_units["TEIN_CAMPUS"],
            },
            {
                "email": "demo.zongo@ndc.example",
                "membership_id": "NDC-DEMO-000027",
                "first_name": "Demo",
                "last_name": "Zongo Caucus Coordinator",
                "role_code": "zongo_caucus_coordinator",
                "unit": auxiliary_units["ZONGO_CAUCUS"],
            },
            {
                "email": "demo.professionals@ndc.example",
                "membership_id": "NDC-DEMO-000028",
                "first_name": "Demo",
                "last_name": "Professionals Forum Convener",
                "role_code": "professionals_forum_convener",
                "unit": auxiliary_units["PROFESSIONALS_FORUM"],
            },
            {
                "email": "demo.externalbranch@ndc.example",
                "membership_id": "NDC-DEMO-000029",
                "first_name": "Demo",
                "last_name": "External Branch Chairman",
                "role_code": "external_branch_chairman",
                "unit": auxiliary_units["EXTERNAL_BRANCH"],
            },
            {
                "email": "demo.elders@ndc.example",
                "membership_id": "NDC-DEMO-000030",
                "first_name": "Demo",
                "last_name": "Council of Elders Chair",
                "role_code": "council_of_elders_chair",
                "unit": auxiliary_units["COUNCIL_OF_ELDERS"],
            },
            {
                "email": "demo.parliamentary@ndc.example",
                "membership_id": "NDC-DEMO-000031",
                "first_name": "Demo",
                "last_name": "Parliamentary Group Leader",
                "role_code": "parliamentary_group_leader",
                "unit": auxiliary_units["PARLIAMENTARY_GROUP"],
            },
            {
                "email": "demo.committee@ndc.example",
                "membership_id": "NDC-DEMO-000032",
                "first_name": "Demo",
                "last_name": "Functional Committee Chair",
                "role_code": "functional_committee_chair",
                "unit": auxiliary_units["FUNCTIONAL_COMMITTEE"],
            },
        ]

        created_count = 0
        updated_count = 0
        skipped_emails = []
        for definition in demo_definitions:
            role = Role.objects(code=definition["role_code"]).first()
            if role is None:
                skipped_emails.append(definition["email"])
                self.stdout.write(
                    self.style.WARNING(
                        f"Role '{definition['role_code']}' not found - skipping "
                        f"{definition['email']}. Run role seeding first."
                    )
                )
                continue

            existing = User.objects(email=definition["email"]).first()
            if existing:
                existing.set_password(demo_password)
                existing.is_superadmin = definition.get("is_superadmin", False)
                existing.role = role
                existing.save()
                updated_count += 1
                continue

            demo_user = User(
                email=definition["email"],
                phone_number="0" + definition["membership_id"][-9:],
                first_name=definition["first_name"],
                last_name=definition["last_name"],
                membership_id=definition["membership_id"],
                organizational_unit=definition["unit"],
                role=role,
                is_superadmin=definition.get("is_superadmin", False),
            )
            demo_user.set_password(demo_password)
            demo_user.save()
            created_count += 1

        # Department assignment is handled uniformly for both newly
        # created and already-existing demo accounts here, rather than
        # inline above, so re-running this command always reconfirms it
        # (e.g. if a definition's department_code ever changes).
        for definition in demo_definitions:
            department_code = definition.get("department_code")
            if not department_code:
                continue
            demo_user = User.objects(email=definition["email"]).first()
            if demo_user:
                self._assign_demo_department_head(
                    demo_user, department_code, definition["unit"]
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo accounts seeded ({created_count} newly created, "
                f"{updated_count} password-refreshed, password: {demo_password})."
            )
        )
        if skipped_emails:
            self.stdout.write(
                self.style.ERROR(
                    f"{len(skipped_emails)} demo account(s) were skipped entirely "
                    f"because their role wasn't found: {', '.join(skipped_emails)}. "
                    "This means the roles list above and the demo account list have "
                    "drifted out of sync - check role_code spelling in "
                    "_seed_demo_accounts against BASE_ROLES."
                )
            )

    def _assign_demo_department_head(self, user, department_code, unit):
        from apps.departments.documents import Department, DepartmentAssignment

        department = Department.objects(code=department_code).first()
        if department is None:
            self.stdout.write(
                self.style.WARNING(
                    f"Department '{department_code}' not found - skipping "
                    f"assignment for {user.email}. Run department seeding first."
                )
            )
            return

        existing_assignment = DepartmentAssignment.objects(
            user=user, department=department, organizational_unit=unit
        ).first()
        if existing_assignment:
            existing_assignment.position = "HEAD"
            existing_assignment.is_active = True
            existing_assignment.save()
        else:
            DepartmentAssignment.objects.create(
                user=user,
                department=department,
                organizational_unit=unit,
                position="HEAD",
                is_active=True,
            )

    def _seed_ground_intelligence_sample_data(self):
        """
        Real, specific complaints, welfare requests, and upward reports
        for the demo units - so the Leader Dashboard's Ground
        Intelligence and AI briefing have genuine substance to work
        with instead of an empty jurisdiction. Written as actual party
        business would read, not placeholder text, since the AI
        briefing quotes from this content directly.
        """
        from apps.accounts.documents import User
        from apps.complaints.documents import Complaint
        from apps.hierarchy.documents import OrganizationalUnit
        from apps.messaging.documents import Report
        from apps.welfare.documents import WelfareRequest

        branch_unit = OrganizationalUnit.objects(code="ndc-demo-branch").first()
        constituency_unit = OrganizationalUnit.objects(
            code="ndc-demo-constituency"
        ).first()
        regional_unit = OrganizationalUnit.objects(code="ndc-demo-regional").first()
        member = User.objects(email="demo.member@ndc.example").first()
        branch_secretary = User.objects(email="demo.branch@ndc.example").first()
        constituency_chairman = User.objects(
            email="demo.constituency@ndc.example"
        ).first()

        if not all(
            [branch_unit, constituency_unit, regional_unit, member, branch_secretary]
        ):
            self.stdout.write(
                self.style.WARNING(
                    "Ground intelligence sample data skipped - demo units or "
                    "accounts not found yet."
                )
            )
            return

        complaints = [
            {
                "submitted_by": member,
                "submitting_unit": branch_unit,
                "target_unit": branch_unit,
                "complaint_type": "COMPLAINT",
                "subject": "Branch office roof leaking during the rainy season",
                "description": (
                    "The roof over the branch office meeting room has been leaking "
                    "since the last heavy rains in June. Members have had to move "
                    "chairs and equipment during meetings, and some campaign "
                    "materials stored there got damaged. Needs a proper repair, "
                    "not another temporary patch."
                ),
            },
            {
                "submitted_by": member,
                "submitting_unit": branch_unit,
                "target_unit": constituency_unit,
                "complaint_type": "COMPLAINT",
                "subject": "Delay in reimbursing transport costs for the voter registration drive",
                "description": (
                    "Branch executives fronted transport costs for the door-to-door "
                    "voter registration exercise in March, and the reimbursement "
                    "promised within two weeks still has not come through, four "
                    "months later. Several members are reluctant to volunteer for "
                    "the next drive until this is settled."
                ),
            },
            {
                "submitted_by": branch_secretary,
                "submitting_unit": branch_unit,
                "target_unit": constituency_unit,
                "complaint_type": "PETITION",
                "subject": "Request to formally recognize the youth wing coordinator",
                "description": (
                    "The branch's youth members have been organizing their own "
                    "activities for over a year under an informal coordinator who "
                    "has done genuinely good work, but has never been formally "
                    "appointed or given a title. This petition asks the "
                    "constituency executive to formalize the position so the "
                    "coordinator can represent the branch at constituency-level "
                    "youth meetings."
                ),
            },
        ]
        for data in complaints:
            if not Complaint.objects(subject=data["subject"]).first():
                Complaint.objects.create(**data)

        welfare_requests = [
            {
                "requester": member,
                "organizational_unit": branch_unit,
                "category": "BEREAVEMENT",
                "amount_requested": 500,
                "description": (
                    "Requesting the branch's bereavement support following the "
                    "passing of my father last month. He was also a long-standing "
                    "member of this branch."
                ),
            },
            {
                "requester": branch_secretary,
                "organizational_unit": branch_unit,
                "category": "MEDICAL",
                "amount_requested": 1200,
                "description": (
                    "A member's child was hospitalized for two weeks after a "
                    "road accident. The family has asked whether the branch "
                    "welfare fund can assist with part of the outstanding "
                    "hospital bill."
                ),
            },
        ]
        for data in welfare_requests:
            if not WelfareRequest.objects(
                requester=data["requester"], description=data["description"]
            ).first():
                WelfareRequest.objects.create(**data)

        reports = [
            {
                "title": "Turnout at the branch town hall was lower than expected",
                "body": (
                    "Only around 30 of the branch's 200 registered members attended "
                    "Saturday's town hall on the new membership dues structure. "
                    "Feedback from those who did attend suggests the meeting was "
                    "scheduled at a time that clashed with market day for many "
                    "traders in the area. Recommend checking with constituency on "
                    "whether other branches have had the same issue before setting "
                    "the next date."
                ),
                "submitted_by": branch_secretary,
                "submitting_unit": branch_unit,
                "target_unit": constituency_unit,
            },
            {
                "title": "Constituency-wide membership registration update",
                "body": (
                    "Registration across the constituency's branches is running "
                    "roughly 15 percent below the same period last year. The "
                    "branch-level roof and reimbursement issues raised separately "
                    "may be contributing to reduced volunteer turnout for door-to-"
                    "door registration. Recommend addressing those before the next "
                    "registration push."
                ),
                "submitted_by": constituency_chairman or branch_secretary,
                "submitting_unit": constituency_unit,
                "target_unit": regional_unit,
            },
        ]
        for data in reports:
            if not Report.objects(title=data["title"]).first():
                Report.objects.create(**data)

        self.stdout.write(
            self.style.SUCCESS(
                "Ground intelligence sample data seeded (complaints, welfare "
                "requests, upward reports)."
            )
        )
