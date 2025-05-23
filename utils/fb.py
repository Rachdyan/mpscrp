from bs4 import BeautifulSoup
import pandas as pd
import re
from selenium.webdriver.common.keys import Keys
from lxml import etree
from datetime import date


def extract_product_data_to_dataframe(product_soup,
                                      original_keyword) -> pd.DataFrame:
    """
    Extracts product information (title, link, price, image link, location)
    from a given HTML snippet, adds the current date, and returns the data
    as a Pandas DataFrame.

    Args:
        html_snippet: A string containing the HTML for a single
        product listing.

    Returns:
        A Pandas DataFrame with one row containing the extracted product data.
        Columns include: 'get_date', 'title', 'link', 'price', 'image_link',
        'location'.
        Returns an empty DataFrame with specified columns if the main product
        card is not found.
    """

    # 1. Get today's date
    today_date_str = date.today().strftime("%Y-%m-%d")

    product_data = {
        'source': 'facebook',
        'original_keyword': original_keyword,
        'title': None,
        'id': None,
        'link': None,
        'price': None,
        'image_link': None,
        'location': None,
        '_image_alt_text': None,  # Internal use for fallbacks
        'get_date': today_date_str
    }

    # Define expected columns for empty DataFrame case
    expected_columns = ['source', 'original_keyword',
                        'title', 'id', 'link', 'price',
                        'image_link', 'location', 'get_date']

    product_card = product_soup.select_one('a')

    # The entire product is within one <a> tag
    # product_card = soup.find('a', role='link')

    if not product_card:
        # If no product card is found, return an empty DataFrame with expected
        # columns
        # or a DataFrame with one row of Nones but with the current date.
        # Let's go with one row of Nones and the current date.
        df = pd.DataFrame([product_data])
        return df[expected_columns]

    # 2. Product Link
    product_data['link'] = product_card.get('href')
    product_data['link'] = "https://facebook.com" + product_data['link']

    match = re.search(r"/item/(\d+)", product_data['link'])
    if match:
        product_data['id'] = match.group(1)

    # 3. Image Link and Alt Text (for fallback)
    img_tag = product_card.find('img')
    if img_tag:
        product_data['image_link'] = img_tag.get('src')
        product_data['_image_alt_text'] = img_tag.get('alt', '')

    # Navigate to the main content divs without relying on their classes
    main_wrapper_divs = product_card.find_all('div', recursive=False)

    if main_wrapper_divs:
        main_wrapper_div = main_wrapper_divs[0]
        content_divs = main_wrapper_div.find_all('div', recursive=False)

        if len(content_divs) == 2:
            text_details_overall_container = content_divs[1]
            detail_section_wrappers = text_details_overall_container.find_all(
                'div', recursive=False)

            if len(detail_section_wrappers) == 3:
                price_section_wrapper = detail_section_wrappers[0]
                title_section_wrapper = detail_section_wrappers[1]
                location_section_wrapper = detail_section_wrappers[2]

                # 4. Price from price_section_wrapper
                price_span_tag = price_section_wrapper.find(
                    lambda tag: tag.name == 'span' and
                    tag.get('dir') == 'auto' and
                    tag.string and
                    tag.string.strip().startswith('Rp')
                )
                if price_span_tag:
                    product_data['price'] = price_span_tag.string.strip()

                # 5. Title from title_section_wrapper
                title_span_tag = title_section_wrapper.find(
                    'span',
                    style=lambda s: s and "-webkit-line-clamp: 2" in s
                )
                if title_span_tag:
                    product_data['title'] = title_span_tag.string.strip()

                # 6. Location from location_section_wrapper
                location_outer_span = location_section_wrapper.find(
                    'span', attrs={'dir': 'auto'})
                if location_outer_span:
                    location_inner_span = location_outer_span.find(
                        lambda tag: tag.name == 'span' and
                        not tag.has_attr('dir') and
                        not (tag.has_attr('style') and "-webkit-line-clamp: 2"
                             in tag.get('style', '')) and
                        tag.string,
                        recursive=False
                    )
                    if location_inner_span:
                        product_data['location'] = location_inner_span\
                            .string.strip()

    # Fallbacks using image alt text if specific elements weren't found
    if product_data['_image_alt_text']:
        alt_text = product_data['_image_alt_text']
        if not product_data['title'] or not product_data['location']:
            if " di " in alt_text:
                parts = alt_text.rsplit(" di ", 1)
                if not product_data['title'] and len(parts) > 0:
                    product_data['title'] = parts[0].strip()
                if not product_data['location'] and len(parts) > 1:
                    product_data['location'] = parts[1].strip()
            elif not product_data['title']:
                product_data['title'] = alt_text.strip()

    # Remove the temporary alt text field before creating the
    # DataFrame for output
    final_data_for_df = {
        k: v for k, v in product_data.items() if k != '_image_alt_text'}

    # Create a Pandas DataFrame from the single product's data
    df = pd.DataFrame([final_data_for_df])

    return df[expected_columns]


def search_marketplace(product_dict,
                       sb):
    sb.uc_click('a[href*="marketplace"]')
    sb.sleep(3)

    keyword = product_dict['name']
    print(f"Searching marketplace for {keyword}..")

    sb.type('input[placeholder*="Marketplace"]', keyword)
    sb.sleep(2)

    sb.click_active_element()
    sb.send_keys('input[placeholder*="Marketplace"]', Keys.RETURN)
    sb.sleep(2)

    print("Changing location to Jakarta..")
    sb.click('//*[@id="seo_filters"]/div[1]/div[1]/div')
    sb.sleep(2)
    sb.type('input[aria-label*="Lokasi"]', "jakarta")
    sb.sleep(4)
    sb.send_keys('input[aria-label*="Lokasi"]', Keys.ARROW_DOWN)
    sb.send_keys('input[aria-label*="Lokasi"]', Keys.RETURN)
    xpath_selector = (
        '//*[contains(@id, "mount_")]/div/div[1]/div/div[4]/div/div/div[1]'
        '/div/div[2]/div/div/div/div[4]/div/div[2]/div/div/div/div/div/div'
        '/div[1]/div/span/span'
    )
    sb.click(xpath_selector)
    sb.sleep(2)
    print("Inputting min and max price")

    min_price = product_dict['min_price']
    max_price = product_dict['max_price']

    sb.type('input[placeholder*="Min"]', min_price)
    sb.sleep(2)
    sb.type('input[placeholder*="Maks"]', max_price)
    sb.sleep(2)
    sb.send_keys('input[placeholder*="Maks"]', Keys.RETURN)
    sb.sleep(5)

    print("Getting page source..")

    page = sb.get_page_source()
    tree = etree.HTML(page)
    xpath_expression = ('//*[contains(@id, "mount_")]/div/div[1]/div/div[3]'
                        '/div/div/div[1]/div[1]/div[2]/div'
                        '/div/div[3]/div/div[2]')

    selected_elements = tree.xpath(xpath_expression)
    # selected_elements

    if selected_elements:
        lxml_element_found = selected_elements[0]

        # 2. Serialize the lxml element to an HTML string
        element_html_string = etree.tostring(
            lxml_element_found, encoding='unicode')

        # 3. Parse this HTML string with BeautifulSoup
        soup = BeautifulSoup(element_html_string, 'html.parser')
        all_products = soup.select('div')

        all_product_df = pd.concat([extract_product_data_to_dataframe(
            product_soup=product,
            original_keyword=keyword
        ) for product in all_products])
        # extract_product_data_to_dataframe(all_products[0])
        all_product_df.drop_duplicates(inplace=True)
        all_product_df = all_product_df[all_product_df.title.notnull()]

        keyword_filter = product_dict['keyword_filter']
        if keyword_filter:
            all_product_df = all_product_df[
                all_product_df['title'].str.lower()
                .str.contains(keyword)]

        print(f"There are {len(all_product_df)} products for {keyword}")
        return all_product_df
