import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import 'volunteer_provider.dart';

class VolunteerOpportunitiesScreen extends StatefulWidget {
  const VolunteerOpportunitiesScreen({super.key});

  @override
  State<VolunteerOpportunitiesScreen> createState() => _VolunteerOpportunitiesScreenState();
}

class _VolunteerOpportunitiesScreenState extends State<VolunteerOpportunitiesScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<VolunteerProvider>().load();
    });
  }

  Future<void> _signUp(String opportunityId) async {
    final provider = context.read<VolunteerProvider>();
    final success = await provider.signUp(opportunityId);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(success ? "You're signed up!" : 'Sign-up failed. Please try again.'),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<VolunteerProvider>();
    final dateFormat = DateFormat('EEE, MMM d - h:mm a');

    return Scaffold(
      appBar: AppBar(title: const Text('Volunteer Opportunities')),
      body: Builder(
        builder: (context) {
          if (provider.isLoading && provider.opportunities.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }
          if (provider.error != null && provider.opportunities.isEmpty) {
            return Center(child: Text(provider.error!));
          }
          if (provider.opportunities.isEmpty) {
            return const Center(child: Text('No open volunteer opportunities right now.'));
          }
          return RefreshIndicator(
            onRefresh: () => context.read<VolunteerProvider>().load(),
            child: ListView.builder(
              padding: const EdgeInsets.all(8),
              itemCount: provider.opportunities.length,
              itemBuilder: (context, index) {
                final opportunity = provider.opportunities[index];
                final alreadySignedUp = provider.isSignedUp(opportunity.id);
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(opportunity.title, style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 4),
                        if (opportunity.description.isNotEmpty) Text(opportunity.description),
                        const SizedBox(height: 8),
                        Text(dateFormat.format(opportunity.scheduledStart)),
                        if (opportunity.location.isNotEmpty) Text(opportunity.location),
                        const SizedBox(height: 8),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text('${opportunity.filledCount} / ${opportunity.neededCount} filled'),
                            if (alreadySignedUp)
                              const Chip(label: Text('Signed up'))
                            else if (opportunity.isFull)
                              const Chip(label: Text('Full'))
                            else
                              FilledButton(
                                onPressed: provider.isSigningUp(opportunity.id)
                                    ? null
                                    : () => _signUp(opportunity.id),
                                child: provider.isSigningUp(opportunity.id)
                                    ? const SizedBox(
                                        height: 16,
                                        width: 16,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          color: Colors.white,
                                        ),
                                      )
                                    : const Text('Sign Up'),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
