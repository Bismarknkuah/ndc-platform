import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import 'welfare_provider.dart';

class WelfareScreen extends StatefulWidget {
  const WelfareScreen({super.key});

  @override
  State<WelfareScreen> createState() => _WelfareScreenState();
}

class _WelfareScreenState extends State<WelfareScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<WelfareProvider>().load();
    });
  }

  void _openSubmitForm() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _SubmitWelfareRequestSheet(),
    );
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'APPROVED':
      case 'DISBURSED':
        return Colors.green;
      case 'REJECTED':
        return Colors.red;
      default:
        return Colors.orange;
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<WelfareProvider>();
    final dateFormat = DateFormat('MMM d, yyyy');

    return Scaffold(
      appBar: AppBar(title: const Text('Welfare Support')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openSubmitForm,
        icon: const Icon(Icons.add),
        label: const Text('Request Support'),
      ),
      body: Builder(
        builder: (context) {
          if (provider.isLoading && provider.myRequests.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }
          if (provider.error != null && provider.myRequests.isEmpty) {
            return Center(child: Text(provider.error!));
          }
          if (provider.myRequests.isEmpty) {
            return const Center(child: Text('No welfare requests yet.'));
          }
          return RefreshIndicator(
            onRefresh: () => context.read<WelfareProvider>().load(),
            child: ListView.builder(
              padding: const EdgeInsets.all(8),
              itemCount: provider.myRequests.length,
              itemBuilder: (context, index) {
                final request = provider.myRequests[index];
                return Card(
                  child: ListTile(
                    title: Text(request.category),
                    subtitle: Text(
                      '${request.description}\nGHS ${request.amountRequested} · '
                      '${dateFormat.format(request.createdAt)}',
                    ),
                    isThreeLine: true,
                    trailing: Chip(
                      label: Text(request.status),
                      backgroundColor: _statusColor(request.status).withOpacity(0.15),
                      labelStyle: TextStyle(color: _statusColor(request.status)),
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

class _SubmitWelfareRequestSheet extends StatefulWidget {
  const _SubmitWelfareRequestSheet();

  @override
  State<_SubmitWelfareRequestSheet> createState() => _SubmitWelfareRequestSheetState();
}

class _SubmitWelfareRequestSheetState extends State<_SubmitWelfareRequestSheet> {
  final _formKey = GlobalKey<FormState>();
  final _descriptionController = TextEditingController();
  final _amountController = TextEditingController();
  String _category = welfareCategories.first;

  @override
  void dispose() {
    _descriptionController.dispose();
    _amountController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    final provider = context.read<WelfareProvider>();
    final success = await provider.submit(
      category: _category,
      description: _descriptionController.text.trim(),
      amountRequested: _amountController.text.trim(),
    );
    if (!mounted) return;
    if (success) {
      Navigator.of(context).pop();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(provider.submitError ?? 'Submission failed.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<WelfareProvider>();
    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Request Welfare Support', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _category,
              decoration: const InputDecoration(labelText: 'Category', border: OutlineInputBorder()),
              items: welfareCategories
                  .map((c) => DropdownMenuItem(value: c, child: Text(c)))
                  .toList(),
              onChanged: (value) => setState(() => _category = value ?? _category),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _descriptionController,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Description',
                border: OutlineInputBorder(),
              ),
              validator: (value) =>
                  (value == null || value.trim().isEmpty) ? 'Please describe your request' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _amountController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                labelText: 'Amount Requested (GHS)',
                border: OutlineInputBorder(),
              ),
              validator: (value) {
                if (value == null || value.trim().isEmpty) return 'Enter an amount';
                if (double.tryParse(value) == null) return 'Enter a valid number';
                return null;
              },
            ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: provider.isSubmitting ? null : _submit,
              child: provider.isSubmitting
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Text('Submit Request'),
            ),
          ],
        ),
      ),
    );
  }
}
