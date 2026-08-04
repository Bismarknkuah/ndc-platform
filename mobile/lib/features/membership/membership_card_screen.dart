import 'dart:convert';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'membership_card_provider.dart';

class MembershipCardScreen extends StatefulWidget {
  const MembershipCardScreen({super.key});

  @override
  State<MembershipCardScreen> createState() => _MembershipCardScreenState();
}

class _MembershipCardScreenState extends State<MembershipCardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<MembershipCardProvider>().load();
    });
  }

  Future<void> _confirmReissue() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Reissue card?'),
        content: const Text(
          'This generates a new QR code and immediately invalidates your '
          'current one. Only do this if your card was lost or compromised.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Reissue'),
          ),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      await context.read<MembershipCardProvider>().reissue();
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<MembershipCardProvider>();

    return Scaffold(
      appBar: AppBar(title: const Text('Membership Card')),
      body: Builder(
        builder: (context) {
          if (provider.isLoading && provider.card == null) {
            return const Center(child: CircularProgressIndicator());
          }
          if (provider.error != null && provider.card == null) {
            return Center(child: Text(provider.error!));
          }
          final card = provider.card!;
          return Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Card(
                elevation: 4,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'NDC Member',
                        style: Theme.of(context).textTheme.labelLarge,
                      ),
                      const SizedBox(height: 16),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.memory(
                          base64Decode(card.qrCodeBase64),
                          width: 220,
                          height: 220,
                          gaplessPlayback: true,
                        ),
                      ),
                      const SizedBox(height: 20),
                      Text(
                        card.fullName,
                        style: Theme.of(context).textTheme.titleLarge,
                        textAlign: TextAlign.center,
                      ),
                      Text(
                        card.membershipId,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              fontFeatures: [const FontFeature.tabularFigures()],
                            ),
                      ),
                      const SizedBox(height: 8),
                      Text(card.role.isEmpty ? 'Ordinary Member' : card.role),
                      Text(
                        card.organizationalUnit,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 24),
                      OutlinedButton.icon(
                        onPressed: provider.isReissuing ? null : _confirmReissue,
                        icon: provider.isReissuing
                            ? const SizedBox(
                                height: 16,
                                width: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.refresh),
                        label: const Text('Report Lost / Reissue'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
