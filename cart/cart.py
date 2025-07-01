from store.models import ProductVariation, Profile # Import ProductVariation
from decimal import Decimal # For handling monetary values precisely
import json # To save/load dictionary to/from JSON string in Profile
from django.shortcuts import get_object_or_404 # Useful for retrieving variations

class Cart():
    """
    A base Cart class, providing default behaviors for managing
    ProductVariations in the session.
    """
    def __init__(self, request):
        self.session = request.session
        self.request = request # Keep request for accessing user

        # Get the current session key if it exists
        cart = self.session.get('session_key')

        # If the user is new or session key doesn't exist, create one
        if 'session_key' not in request.session:
            cart = self.session['session_key'] = {}

        # Make sure cart is available on all pages of site
        # self.cart will be a dictionary like { 'variation_id_str': quantity, ... }
        self.cart = cart

        # Load cart from database if user is authenticated and has an old cart
        # This should happen ONLY when the user logs in, not on every page load.
        # The login view should handle loading the cart from the profile.
        # However, your original __init__ seemed to imply loading here.
        # Let's refactor the loading logic slightly.
        # If the cart is empty AND the user is logged in AND they have an old cart...
        if not self.cart and self.request.user.is_authenticated:
             self._load_from_db() # Call helper method to load from DB


    def add(self, variation, quantity):
        """
        Add a ProductVariation to the cart or update its quantity.
        Accepts ProductVariation object and integer quantity.
        """
        # Use variation ID as the key (as string)
        variation_id_str = str(variation.id)
        quantity = int(quantity) # Ensure quantity is int

        # Add or update quantity for this variation
        # Use .get() with a default of 0 to handle adding to an existing item
        self.cart[variation_id_str] = self.cart.get(variation_id_str, 0) + quantity

        self.session.modified = True # Mark session as modified

        # Save the updated cart to the database if user is logged in
        self._save_to_db()

    # Removed db_add as it's redundant with the updated add method and loading logic

    def cart_total(self):
        """
        Calculate the total price of all items in the cart.
        Uses the effective price of each variation.
        """
        total = Decimal(0)
        # Get the IDs of variations currently in the cart
        variation_ids = self.cart.keys()

        # Query the database for the corresponding ProductVariation objects
        # Use get_object_or_404 is not suitable here, filter handles multiple IDs
        # Use a list comprehension or filter to get the variations
        variations = ProductVariation.objects.filter(id__in=variation_ids)

        # Create a mapping from variation ID (string) to object for quick lookup
        variation_map = {str(v.id): v for v in variations}

        # Iterate through the items in the cart dictionary (variation_id_str: quantity)
        for variation_id_str, quantity in self.cart.items():
            # Check if the variation object was found in the database query
            if variation_id_str in variation_map:
                variation = variation_map[variation_id_str]
                # Add the subtotal for this item (effective price * quantity) to the total
                total += (variation.get_effective_price() * Decimal(quantity))
            # else: # Optional: Handle cases where a variation in session no longer exists in DB
            #     print(f"Warning: Variation ID {variation_id_str} in cart session not found in DB.")
            #     # You might want to remove this invalid item from the session here

        return total

    def __len__(self):
        """
        Return the total quantity of items in the cart (sum of quantities).
        """
        # Sum the quantities stored as values in the cart dictionary
        return sum(self.cart.values())

    # Removed get_prods and get_quants as __iter__ provides the necessary data structure

    def __iter__(self):
        """
        Iterate over the items in the cart and retrieve the ProductVariation objects
        from the database. Yields dictionaries containing variation object, quantity, and subtotal.
        """
        # Get the IDs of variations currently in the cart
        variation_ids = self.cart.keys()

        # Query the database for the corresponding ProductVariation objects
        variations = ProductVariation.objects.filter(id__in=variation_ids)

        # Create a mapping from variation ID (string) to object for quick lookup
        variation_map = {str(v.id): v for v in variations}

        # Iterate through the items in the cart dictionary (variation_id_str: quantity)
        for variation_id_str, quantity in self.cart.items():
            # Check if the variation object was found in the database query
            if variation_id_str in variation_map:
                variation = variation_map[variation_id_str]
                # Calculate subtotal for this item
                subtotal = variation.get_effective_price() * Decimal(quantity)
                # Yield a dictionary with the item details
                yield {
                    'variation': variation,
                    'quantity': quantity,
                    'subtotal': subtotal,
                }
            # else: # Optional: Handle items in session but not in DB (they won't be yielded)
            #     pass


    def update(self, variation, quantity):
        """
        Update the quantity of a specific ProductVariation in the cart.
        Accepts variation_id (int or str) and integer quantity.
        """
        variation_id_str = str(variation) # Ensure variation ID is a string key
        quantity = int(quantity) # Ensure quantity is int

        # Check if the item exists and the new quantity is valid
        if variation_id_str in self.cart and quantity >= 0:
             # If quantity is 0, remove the item (or handle this in delete method)
             if quantity == 0:
                 self.delete(variation_id_str) # Use the delete method
             else:
                 # Update the quantity
                 self.cart[variation_id_str] = quantity
                 self.session.modified = True # Mark session as modified
                 self._save_to_db() # Save changes to DB if logged in
        # Optional: Handle case where variation_id is not in cart


    def delete(self, variation):
        """
        Delete a specific ProductVariation from the cart.
        Accepts variation_id (int or str).
        """
        variation_id_str = str(variation) # Ensure variation ID is a string key

        # Delete from dictionary/cart if it exists
        if variation_id_str in self.cart:
            del self.cart[variation_id_str]
            self.session.modified = True # Mark session as modified
            self._save_to_db() # Save changes to DB if logged in

    # --- Database Persistence Helper Methods ---

    def _save_to_db(self):
        """
        Helper method to save the current cart state to the user's profile
        if the user is authenticated.
        """
        if self.request.user.is_authenticated:
            try:
                # Get the current user profile
                profile = Profile.objects.get(user=self.request.user)
                # Save the current cart dictionary as a JSON string
                # self.cart already has variation_id_str keys and quantity values
                profile.old_cart = json.dumps(self.cart)
                profile.save()
            except Profile.DoesNotExist:
                # This should ideally not happen if the post_save signal works,
                # but handle it just in case.
                print(f"Warning: Profile not found for user {self.request.user.username}")
            except Exception as e:
                 print(f"Error saving cart to DB for user {self.request.user.username}: {e}")


    def _load_from_db(self):
        """
        Helper method to load the cart from the user's profile database field
        and merge it with the current session cart.
        This should ideally be called ONCE upon successful user login.
        """
        if self.request.user.is_authenticated:
            try:
                profile = Profile.objects.get(user=self.request.user)
                if profile.old_cart:
                    # Load the cart dictionary from the JSON string
                    loaded_cart = json.loads(profile.old_cart)

                    # Merge the loaded cart with the current session cart
                    # If a variation exists in both, sum quantities
                    # If only in loaded_cart, add it to session cart
                    for variation_id_str, quantity in loaded_cart.items():
                         # Ensure quantity is int (JSON might load as float/string)
                         try:
                            quantity = int(quantity)
                            if quantity > 0: # Only add valid quantities
                                self.cart[variation_id_str] = self.cart.get(variation_id_str, 0) + quantity
                         except ValueError:
                              print(f"Warning: Invalid quantity '{quantity}' found for variation ID {variation_id_str} in old_cart.")
                              pass # Skip invalid items

                    # Clear the old_cart field in the profile after loading
                    # to prevent loading the same items multiple times on subsequent logins
                    profile.old_cart = ""
                    profile.save()

                    # Mark session as modified after merging
                    self.session.modified = True
                    print(f"Cart loaded and merged from DB for user {self.request.user.username}")

            except Profile.DoesNotExist:
                print(f"Warning: Profile not found for user {self.request.user.username} during cart load.")
            except json.JSONDecodeError:
                 print(f"Error decoding old_cart JSON for user {self.request.user.username}.")
                 # You might want to clear the invalid old_cart here: profile.old_cart = ""; profile.save()
            except Exception as e:
                 print(f"Error loading cart from DB for user {self.request.user.username}: {e}")