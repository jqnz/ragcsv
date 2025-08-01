from bs4 import BeautifulSoup
import pandas as pd
from typing import Dict, List, Optional
import os

class BookingHTMLParser:
    def __init__(self, html_path: str):
        """
        Initialize the parser with the path to the Booking.com HTML file.
        
        Args:
            html_path: Path to the HTML file to parse
        """
        self.html_path = html_path
        self.soup = None
        
    def load_html(self):
        """Load and parse the HTML file."""
        with open(self.html_path, 'r', encoding='utf-8') as f:
            self.soup = BeautifulSoup(f, 'html.parser')
    
    def extract_room_data(self) -> List[Dict]:
        """
        Extract room availability data from the HTML.
        
        Returns:
            List of dictionaries containing room information
        """
        if not self.soup:
            self.load_html()
            
        rooms = []
        
        # Find all room rows in the availability table
        room_rows = self.soup.select('.js-rt-block-row.e2e-hprt-table-row')
        
        for row in room_rows:
            room_data = {}
            
            # Extract room type
            room_type_elem = row.select_one('.hprt-roomtype-icon-link')
            room_type = room_type_elem.get_text(strip=True) if room_type_elem else 'N/A'
            if room_type != 'N/A':
                current_room_type = room_type
            else:
                room_type = current_room_type
            room_data['room_type'] = room_type
            
            # Extract room description
            description_elem = row.select_one('.hprt-roomtype-link')
            room_data['description'] = description_elem.get_text(' ', strip=True) if description_elem else 'N/A'
            
            # Extract price
            price_elem = row.select_one('.prco-valign-middle-helper')
            room_data['price'] = price_elem.get_text(strip=True) if price_elem else 'N/A'
            
            # Extract cancellation policy
            policy_elem = row.select_one('.hprt-conditions-ntf')
            room_data['cancellation_policy'] = policy_elem.get_text(strip=True) if policy_elem else 'N/A'
            
            # Extract max occupancy
            occupancy_elem = row.select_one('.hprt-occupancy-occupancy-info')
            room_data['max_occupancy'] = occupancy_elem.get_text(strip=True) if occupancy_elem else 'N/A'
            room_data['max_occupancy'] = room_data['max_occupancy'].split(':')[-1].strip()
            
            # Extract number of available units
            select_elem = row.select_one('select.hprt-nos-select')
            if select_elem:
                # The number of options minus 1 (the '0' option) gives available units
                available_units = len(select_elem.find_all('option')) - 1
                room_data['available_units'] = available_units
                
                # Also get the price from the last option if available
                last_option = select_elem.find_all('option')[-1]
                if last_option and available_units > 0:
                    # Extract price from the option text (e.g., "1 ($6,584)")
                    option_text = last_option.get_text(strip=True)
                    if '$' in option_text:
                        price = option_text.split('$')[-1].split(')')[0].replace(',', '')
                        room_data['price_per_unit'] = f"{price}"
                else:
                    room_data['price_per_unit'] = 'N/A'
            else:
                room_data['available_units'] = 0
                room_data['price_per_unit'] = 'N/A'
            
            # Check for breakfast information in the policy modal
            policy_modal = row.find_next('template', id=lambda x: x and x.startswith('policyModal_'))
            
            # First, check for the breakfast icon directly in the row
            breakfast_icon = row.select_one('.bk-icon.-streamline-food_coffee')
            if breakfast_icon:
                # Check the fill color of the SVG to determine if breakfast is included
                fill_color = breakfast_icon.get('fill', '').lower()
                if fill_color == '#008009':  # Green color indicates breakfast is included
                    room_data['breakfast_included'] = 'Yes'
                else:
                    room_data['breakfast_included'] = 'No'
            else:
                room_data['breakfast_included'] = 'No'
            
            # Still check the policy modal for more detailed meal information
            if policy_modal:
                # Look for the meals section
                meals_section = policy_modal.find('h3', string='Meals')
                if meals_section:
                    # Find the description div that contains the meal details
                    meals_info = meals_section.find_next('div', class_='bui-list__description')
                    if meals_info:
                        meals_text = meals_info.get_text(strip=True)
                        room_data['meals_included'] = meals_text
                        # If we found detailed meal info, update the breakfast status
                        if 'breakfast' in meals_text.lower() and room_data['breakfast_included'] == 'No':
                            room_data['breakfast_included'] = 'Yes'
                    else:
                        room_data['meals_included'] = 'Not specified'
                else:
                    room_data['meals_included'] = 'No meals included'
            else:
                room_data['meals_included'] = 'Not specified'
            
            rooms.append(room_data)
            
        return rooms
    
    def get_availability_table(self) -> pd.DataFrame:
        """
        Get the availability data as a pandas DataFrame.
        
        Returns:
            DataFrame containing the room availability information
        """
        room_data = self.extract_room_data()
        return pd.DataFrame(room_data)

def main():
    # Get the absolute path to the HTML file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(os.path.dirname(current_dir), 'data', 'booking_2025-08-07_2025-08-08.html')
    
    # Parse the HTML and get availability
    parser = BookingHTMLParser(html_path)
    df = parser.get_availability_table()
    
    # Display the results
    print("\n=== Booking.com Room Availability ===")
    print(f"Found {len(df)} room types\n")
    
    # Print the DataFrame without truncation
    with pd.option_context('display.max_columns', None, 'display.width', None, 'display.max_colwidth', 50):
        print(df)
    
    # Save to CSV
    output_path = os.path.join(os.path.dirname(current_dir), 'data', 'booking_availability.csv')
    df.to_csv(output_path, index=False)
    print(f"\nData saved to: {output_path}")

if __name__ == "__main__":
    main()