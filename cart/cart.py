from store.models import Product, ProductVariation, Profile
from decimal import Decimal # For handling monetary values precisely
import json # To save/load dictionary to/from JSON string in Profile
from django.shortcuts import get_object_or_404 # Useful for retrieving objects
# Importy dla efektywnego pobierania wielu obiektów
from django.db.models import Q

class Cart():
    """
    A base Cart class, providing default behaviors for managing
    Products and ProductVariations in the session.
    """
    def __init__(self, request):
        self.session = request.session
        self.request = request # Keep request for accessing user

        # Get the current session key if it exists
        # Używamy stałego klucza dla koszyka w sesji
        cart = self.session.get('cart_session_key') # Zmieniono nazwę klucza dla jasności

        # If the user is new or session key doesn't exist, create one
        if 'cart_session_key' not in request.session:
            cart = self.session['cart_session_key'] = {}

        # self.cart will be a dictionary like { 'p_product_id_str': quantity, 'v_variation_id_str': quantity, ... }
        self.cart = cart

        # Load cart from database if user is authenticated and has an old cart
        # This logic loads from DB only if the session cart is currently empty.
        if not self.cart and self.request.user.is_authenticated:
             self._load_from_db() # Call helper method to load from DB


    # Zmieniamy metodę add, aby akceptowała obiekt Product LUB ProductVariation
    def add(self, item, quantity):
        """
        Add a Product or ProductVariation to the cart or update its quantity.
        Accepts item object (Product or ProductVariation instance) and integer quantity.
        """
        quantity = int(quantity) # Ensure quantity is int

        # Determine the type and construct the key
        if isinstance(item, ProductVariation):
            item_key = f"v_{item.id}"
        elif isinstance(item, Product):
            item_key = f"p_{item.id}"
        else:
            # Raise an error or handle unsupported item types
            raise TypeError("Unsupported item type added to cart. Must be Product or ProductVariation.")

        # Add or update quantity for this item
        # Use .get() with a default of 0 to handle adding to an existing item
        self.cart[item_key] = self.cart.get(item_key, 0) + quantity

        self.session.modified = True # Mark session as modified

        # Save the updated cart to the database if user is logged in
        self._save_to_db()

    def cart_total(self):
        """
        Calculate the total price of all items in the cart.
        Uses the effective price of each item (Product or Variation).
        """
        total = Decimal(0)
        # Get the keys of items currently in the cart
        item_keys = self.cart.keys()

        # Separate Product and Variation IDs
        # Używamy listy do przechowywania ID, a następnie filtrujemy bazę danych
        product_ids = []
        variation_ids = []
        for key in item_keys:
            try:
                if key.startswith('p_'):
                    product_ids.append(int(key.split('_')[1]))
                elif key.startswith('v_'):
                    variation_ids.append(int(key.split('_')[1]))
            except (IndexError, ValueError):
                # Handle invalid keys if any exist in the session (e.g., from old format)
                print(f"Warning: Invalid item key format in cart session: {key}")
                # Optionally remove invalid key: del self.cart[key]; self.session.modified = True

        # Query the database for the corresponding objects efficiently
        products = Product.objects.filter(id__in=product_ids)
        variations = ProductVariation.objects.filter(id__in=variation_ids)

        # Create mappings for quick lookup by item_key
        product_map = {f"p_{p.id}": p for p in products}
        variation_map = {f"v_{v.id}": v for v in variations}

        # Iterate through the items in the cart dictionary (item_key: quantity)
        for item_key, quantity in self.cart.items():
            item = None
            if item_key.startswith('p_') and item_key in product_map:
                item = product_map[item_key]
            elif item_key.startswith('v_') and item_key in variation_map:
                item = variation_map[item_key]
            # else: # Item not found in map (means it didn't exist in DB query) - will be skipped

            if item:
                # Get the effective price (ProductVariation inherits from Product's effective price)
                # Product also has get_effective_price
                total += (item.get_effective_price() * Decimal(quantity))
            # else: # Optional: Handle items in session that no longer exist in DB
            #     print(f"Warning: Item key {item_key} in cart session not found in DB.")
            #     # You might want to remove this invalid item from the session here
            #     # del self.cart[item_key] # Be careful modifying during iteration
            #     # self.session.modified = True


        return total

    def __len__(self):
        """
        Return the total quantity of items in the cart (sum of quantities).
        """
        # Sum the quantities stored as values in the cart dictionary
        return sum(self.cart.values())

    def get_total_quantity(self):
        """Helper method to get total quantity."""
        return self.__len__()


    def __iter__(self):
        """
        Iterate over the items in the cart and retrieve the corresponding objects
        from the database. Yields dictionaries containing item object, quantity, and subtotal.
        """
        item_keys = self.cart.keys()

        # Separate Product and Variation IDs
        product_ids = []
        variation_ids = []
        for key in item_keys:
            try:
                if key.startswith('p_'):
                    product_ids.append(int(key.split('_')[1]))
                elif key.startswith('v_'):
                    variation_ids.append(int(key.split('_')[1]))
            except (IndexError, ValueError):
                 # Handle invalid keys if any exist
                 continue # Skip this key


        # Query the database for the corresponding objects efficiently
        products = Product.objects.filter(id__in=product_ids)
        variations = ProductVariation.objects.filter(id__in=variation_ids)

        # Create mappings for quick lookup by item_key
        product_map = {f"p_{p.id}": p for p in products}
        variation_map = {f"v_{v.id}": v for v in variations}

        # Iterate through the items in the cart dictionary (item_key: quantity)
        # To ensure consistent order, you might want to sort item_keys first
        # sorted_item_keys = sorted(self.cart.keys())
        # for item_key in sorted_item_keys:
        for item_key, quantity in self.cart.items():
            item_object = None
            item_type = None

            if item_key.startswith('p_') and item_key in product_map:
                item_object = product_map[item_key]
                item_type = 'product' # Add type information
            elif item_key.startswith('v_') and item_key in variation_map:
                item_object = variation_map[item_key]
                item_type = 'variation' # Add type information
            else:
                 # Item not found in DB, skip it
                 continue # Skip to the next item in the cart

            # Calculate subtotal for this item
            subtotal = item_object.get_effective_price() * Decimal(quantity)

            # Yield a dictionary with the item details
            # Include the item_key for update/delete operations
            yield {
                'item_key': item_key, # The key used in the session cart (e.g., 'p_123', 'v_456')
                'item_object': item_object, # The actual Product or ProductVariation object
                'item_type': item_type, # 'product' or 'variation'
                'quantity': quantity,
                'subtotal': subtotal,
            }


    def update(self, item_key, quantity):
        """
        Update the quantity of a specific item (Product or ProductVariation) in the cart.
        Accepts item_key (string like 'p_123' or 'v_456') and integer quantity.
        """
        quantity = int(quantity) # Ensure quantity is int

        # Check if the item exists in the cart
        if item_key in self.cart:
             if quantity >= 0: # Allow 0 quantity to remove item
                 if quantity == 0:
                     self.delete(item_key) # Use the delete method
                 else:
                     # Update the quantity
                     self.cart[item_key] = quantity
                     self.session.modified = True # Mark session as modified
                     self._save_to_db() # Save changes to DB if logged in
             # Optional: Handle negative quantity attempt
        # Optional: Handle case where item_key is not in cart


    def delete(self, item_key):
        """
        Delete a specific item (Product or ProductVariation) from the cart.
        Accepts item_key (string like 'p_123' or 'v_456').
        """
        # Delete from dictionary/cart if it exists
        if item_key in self.cart:
            del self.cart[item_key]
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
                profile = Profile.objects.get(user=self.request.user)
                # Save the current cart dictionary as a JSON string
                # self.cart has keys like 'p_123', 'v_456' and quantity values
                profile.old_cart = json.dumps(self.cart)
                profile.save()
                # print(f"Cart saved to DB for user {self.request.user.username}") # Debug
            except Profile.DoesNotExist:
                print(f"Warning: Profile not found for user {self.request.user.username} during cart save.")
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
                    print(f"Attempting to load cart from DB: {loaded_cart}") # Debug

                    # Merge the loaded cart with the current session cart
                    # If an item exists in both, sum quantities
                    # If only in loaded_cart, add it to session cart
                    for item_key, quantity in loaded_cart.items():
                         # Ensure quantity is int
                         try:
                            quantity = int(quantity)
                            if quantity > 0: # Only add valid quantities
                                # Check if the item still exists in the database before adding
                                item_object = None
                                if item_key.startswith('p_'):
                                    try:
                                        product_id = int(item_key.split('_')[1])
                                        item_object = Product.objects.get(id=product_id)
                                    except (IndexError, ValueError, Product.DoesNotExist):
                                        pass # Item key invalid or product not found
                                elif item_key.startswith('v_'):
                                     try:
                                        variation_id = int(item_key.split('_')[1])
                                        item_object = ProductVariation.objects.get(id=variation_id)
                                     except (IndexError, ValueError, ProductVariation.DoesNotExist):
                                         pass # Item key invalid or variation not found
                                else:
                                     # Handle invalid keys in old_cart (old format?)
                                     print(f"Warning: Invalid item key format '{item_key}' found in old_cart. Skipping item.")
                                     continue # Skip this item

                                if item_object: # Only add if the item still exists in DB
                                    # Check stock before adding from saved cart
                                    available_stock = item_object.stock if isinstance(item_object, Product) else item_object.stock
                                    actual_quantity_to_add = min(quantity, available_stock) # Don't add more than available

                                    if actual_quantity_to_add > 0:
                                         # Add to session cart, summing with existing quantity if any
                                         self.cart[item_key] = self.cart.get(item_key, 0) + actual_quantity_to_add
                                         print(f"Loaded and added item {item_key} with quantity {actual_quantity_to_add} from DB.") # Debug
                                    else:
                                         print(f"Item {item_key} from old_cart has no stock available. Skipping.") # Debug

                                else:
                                     print(f"Warning: Item key {item_key} from old_cart not found in DB. Skipping.")


                         except ValueError:
                              print(f"Warning: Invalid quantity '{quantity}' found for item key {item_key} in old_cart. Skipping item.")
                              pass # Skip invalid items
                         except Exception as e:
                              print(f"Unexpected error processing item {item_key} from old_cart: {e}")
                              pass


                    # Clear the old_cart field in the profile after loading
                    # to prevent loading the same items multiple times on subsequent logins
                    profile.old_cart = ""
                    profile.save()

                    # Mark session as modified after merging
                    self.session.modified = True
                    print(f"Cart loaded and merged from DB for user {self.request.user.username}. Final session cart: {self.cart}") # Debug

            except Profile.DoesNotExist:
                print(f"Warning: Profile not found for user {self.request.user.username} during cart load.")
            except json.JSONDecodeError:
                 print(f"Error decoding old_cart JSON for user {self.request.user.username}. Clearing invalid data.")
                 # Clear the invalid data to prevent repeated errors
                 try:
                     profile = Profile.objects.get(user=self.request.user)
                     profile.old_cart = ""
                     profile.save()
                 except Profile.DoesNotExist:
                     pass # Cannot save if profile doesn't exist
                 except Exception as e:
                      print(f"Error clearing invalid old_cart for user {self.request.user.username}: {e}")

            except Exception as e:
                 print(f"Unexpected error loading cart from DB for user {self.request.user.username}: {e}")