from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import ClientProfile


class Command(BaseCommand):
    help = 'Create demo users for testing (10 users + 1 admin)'

    def handle(self, *args, **options):
        # Create superadmin if not exists
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@invywed.com',
                'first_name': 'Super',
                'last_name': 'Admin',
                'is_superuser': True,
                'is_staff': True,
                'is_active': True,
            }
        )
        
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(self.style.SUCCESS('Created superadmin: admin / admin123'))
        else:
            # Update password if exists
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(self.style.SUCCESS('Updated superadmin password: admin / admin123'))
        
        # Create ClientProfile for admin if not exists
        ClientProfile.objects.get_or_create(
            user=admin,
            defaults={
                'phone_number': '081234567890',
                'whatsapp_number': '081234567890',
                'subscription_type': 'platinum',
                'account_level': 'enterprise',
            }
        )
        
        # Create 10 demo users
        demo_users_data = [
            {'username': 'user1', 'email': 'user1@demo.com', 'first_name': 'User', 'last_name': 'Satu'},
            {'username': 'user2', 'email': 'user2@demo.com', 'first_name': 'User', 'last_name': 'Dua'},
            {'username': 'user3', 'email': 'user3@demo.com', 'first_name': 'User', 'last_name': 'Tiga'},
            {'username': 'user4', 'email': 'user4@demo.com', 'first_name': 'User', 'last_name': 'Empat'},
            {'username': 'user5', 'email': 'user5@demo.com', 'first_name': 'User', 'last_name': 'Lima'},
            {'username': 'user6', 'email': 'user6@demo.com', 'first_name': 'User', 'last_name': 'Enam'},
            {'username': 'user7', 'email': 'user7@demo.com', 'first_name': 'User', 'last_name': 'Tujuh'},
            {'username': 'user8', 'email': 'user8@demo.com', 'first_name': 'User', 'last_name': 'Delapan'},
            {'username': 'user9', 'email': 'user9@demo.com', 'first_name': 'User', 'last_name': 'Sembilan'},
            {'username': 'user10', 'email': 'user10@demo.com', 'first_name': 'User', 'last_name': 'Sepuluh'},
        ]
        
        created_count = 0
        updated_count = 0
        
        for user_data in demo_users_data:
            # Check if user exists
            try:
                user = User.objects.get(username=user_data['username'])
                # User exists, update it
                user.email = user_data['email']
                user.first_name = user_data['first_name']
                user.last_name = user_data['last_name']
                user.is_superuser = False
                user.is_staff = False
                user.is_active = True
                user.set_password('demo123')
                user.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'Updated user: {user.username} / demo123'))
            except User.DoesNotExist:
                # User doesn't exist, create it
                try:
                    user = User.objects.create_user(
                        username=user_data['username'],
                        email=user_data['email'],
                        first_name=user_data['first_name'],
                        last_name=user_data['last_name'],
                        password='demo123',
                        is_superuser=False,
                        is_staff=False,
                        is_active=True,
                    )
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Created user: {user.username} / demo123'))
                except Exception as e:
                    # If still duplicate (IntegrityError), try to get it and update
                    from django.db import IntegrityError
                    if isinstance(e, IntegrityError) or 'Duplicate' in str(e):
                        try:
                            user = User.objects.get(username=user_data['username'])
                            user.email = user_data['email']
                            user.first_name = user_data['first_name']
                            user.last_name = user_data['last_name']
                            user.is_superuser = False
                            user.is_staff = False
                            user.is_active = True
                            user.set_password('demo123')
                            user.save()
                            updated_count += 1
                            self.stdout.write(self.style.WARNING(f'Updated user (after duplicate): {user.username} / demo123'))
                        except User.DoesNotExist:
                            self.stdout.write(self.style.ERROR(f'Error with {user_data["username"]}: {str(e)}'))
                            continue
                    else:
                        self.stdout.write(self.style.ERROR(f'Error with {user_data["username"]}: {str(e)}'))
                        continue
            
            # Ensure user is saved
            if not user.pk:
                user.save()
            
            # Create ClientProfile for each user
            try:
                client_profile = ClientProfile.objects.get(user=user)
                # Already exists, skip
            except ClientProfile.DoesNotExist:
                phone_suffix = user_data["username"][-1] if len(user_data["username"]) > 4 else "0"
                client_profile = ClientProfile.objects.create(
                    user=user,
                    phone_number=f'0812345678{phone_suffix}',
                    whatsapp_number=f'0812345678{phone_suffix}',
                    subscription_type='free',
                    account_level='trial',
                )
                self.stdout.write(self.style.SUCCESS(f'  -> Created ClientProfile for {user.username}'))
        
        self.stdout.write(self.style.SUCCESS('\nSummary:'))
        self.stdout.write(self.style.SUCCESS(f'  - Superadmin: admin / admin123'))
        self.stdout.write(self.style.SUCCESS(f'  - Created users: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'  - Updated users: {updated_count}'))
        self.stdout.write(self.style.SUCCESS(f'  - Total demo users: {created_count + updated_count}'))
        self.stdout.write(self.style.SUCCESS('\nAll demo users password: demo123'))

