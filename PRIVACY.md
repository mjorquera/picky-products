# Privacy Policy

**Last updated: May 2026**

## Overview

Picky Products is a personal automation tool built to create and schedule Pinterest pins for an affiliate marketing account. It is not a public-facing product or service.

## Data collected

This tool does not collect, store, or process data from any end users. It operates exclusively on behalf of a single account owner (the developer) to automate content publishing to their own Pinterest account.

The following data is used during operation:

- **Pinterest account access tokens** — used to authenticate API requests to the account owner's Pinterest account. Stored locally in a `.env` file on the developer's machine. Never transmitted to third parties.
- **Notion workspace data** — product names, pin titles, descriptions, and affiliate links stored in the developer's own Notion workspace. Accessed via Notion's official API using the developer's own integration token.
- **Amazon product data** — publicly available product information (titles, images, prices) from Amazon UK, used to generate pin content.

## Third-party services

This tool integrates with:

- [Pinterest API v5](https://developers.pinterest.com/) — to create and schedule pins on the account owner's Pinterest Business account
- [Notion API](https://developers.notion.com/) — to read and update content stored in the developer's own Notion workspace
- [Amazon Associates](https://affiliate-program.amazon.co.uk/) — affiliate programme for monetisation

Each service is subject to its own privacy policy and terms of use.

## Data retention

No data is stored by this tool beyond what is written to the developer's local filesystem and their own Notion workspace. No databases, servers, or cloud storage are used.

## Contact

For any questions, contact: mariojz@gmail.com
